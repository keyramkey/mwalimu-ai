import os
import re
import gradio as gr
from google import genai
from dotenv import load_dotenv
import edge_tts
import asyncio
import tempfile

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ======================
# MASOMO YA TANZANIA (Form 1 - Form 6)
# ======================
SUBJECTS = {
    "Kidato cha 1": [
        "Hisabati", "Kiswahili", "English Language", "Biology", 
        "Geography", "History", "Civics", "Physics", "Chemistry", "Agriculture"
    ],
    "Kidato cha 2": [
        "Hisabati", "Kiswahili", "English Language", "Biology", 
        "Geography", "History", "Civics", "Physics", "Chemistry", "Agriculture"
    ],
    "Kidato cha 3": [
        "Hisabati", "Kiswahili", "English Language", "Biology", 
        "Geography", "History", "Civics", "Physics", "Chemistry", 
        "Agriculture", "Computer Science", "Business Studies"
    ],
    "Kidato cha 4": [
        "Hisabati", "Kiswahili", "English Language", "Biology", 
        "Geography", "History", "Civics", "Physics", "Chemistry", 
        "Agriculture", "Computer Science", "Business Studies", "Additional Mathematics"
    ],
    "Kidato cha 5": [
        "Advanced Mathematics", "Physics", "Chemistry", "Biology",
        "Geography", "History", "Economics", "Accountancy", 
        "Kiswahili", "English Language", "Literature in English"
    ],
    "Kidato cha 6": [
        "Advanced Mathematics", "Physics", "Chemistry", "Biology",
        "Geography", "History", "Economics", "Accountancy", 
        "Kiswahili", "English Language", "Literature in English"
    ]
}

# Walimu na sauti zao
TEACHERS = {
    "Mwalimu Juma": {"voice": "sw-TZ-DaudiNeural", "lang": "sw"},
    "Bi. Amina": {"voice": "sw-TZ-ZuriNeural", "lang": "sw"},
    "Mr. John": {"voice": "en-US-GuyNeural", "lang": "en"},
    "Ms. Sarah": {"voice": "en-US-JennyNeural", "lang": "en"},
}

def get_system_prompt(kidato: str, somo: str, teacher: str) -> str:
    if TEACHERS[teacher]["lang"] == "en":
        return f"""
You are {teacher}, a professional Form {kidato[-1]} teacher in Tanzania teaching {somo}.
- Teach clearly step by step using simple English.
- Use everyday examples.
- Check understanding often.
- Be patient and encouraging.
- Speak as a real classroom teacher.
"""
    else:
        return f"""
Wewe ni {teacher}, mwalimu wa {kidato} unayefundisha somo la {somo} nchini Tanzania.
- Unazungumza Kiswahili sanifu, rahisi na chenye heshima.
- Unafundisha hatua kwa hatua kwa mifano ya maisha ya kila siku.
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa.
- Unatoa pongezi na unamrekebisha kwa upole.
- Unafundisha kama mwalimu wa kweli darasani.
"""

def clean_text_for_tts(text: str) -> str:
    if not text:
        return ""
    # Ondoa LaTeX & Markdown
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Herufi za hesabu
    text = re.sub(r'\b([xX])\b', 'eks', text)
    text = re.sub(r'\b([yY])\b', 'wai', text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

async def text_to_speech(text: str, voice: str):
    try:
        clean = clean_text_for_tts(text)
        if not clean:
            return None
        communicate = edge_tts.Communicate(clean, voice, rate="+8%")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def get_ai_response(message, history, kidato, somo, teacher):
    if not client:
        return "Samahani, API Key haipo."

    try:
        contents = []
        for item in (history or []):
            if isinstance(item, dict):
                role = "user" if item["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": str(item["content"])}]})

        contents.append({"role": "user", "parts": [{"text": message}]})

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config={
                "system_instruction": get_system_prompt(kidato, somo, teacher),
                "temperature": 0.65,
            }
        )
        return response.text.strip()
    except Exception as e:
        return f"Samahani, nimepata hitilafu.\n\n({str(e)})"

def respond(message, history, kidato, somo, teacher):
    user_text = (message or "").strip()
    if not user_text:
        return history, None, ""

    bot_response = get_ai_response(user_text, history, kidato, somo, teacher)
    new_history = (history or []) + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": bot_response}
    ]

    voice = TEACHERS[teacher]["voice"]
    try:
        audio_path = asyncio.run(text_to_speech(bot_response, voice))
    except:
        audio_path = None

    return new_history, audio_path, ""

def update_subjects(kidato):
    return gr.update(choices=SUBJECTS.get(kidato, []), value=SUBJECTS.get(kidato, [""])[0])

# ======================
# UI NZURI SANA
# ======================
custom_css = """
.gradio-container {
    max-width: 1000px !important;
    margin: auto;
    font-family: 'Segoe UI', system-ui, sans-serif;
}
.main-title {
    text-align: center;
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 20px;
}
#chatbot {
    height: 460px !important;
    border-radius: 16px !important;
}
.control-card {
    background: #fff7ed;
    border-radius: 14px;
    padding: 16px;
    border: 1px solid #fed7aa;
}
"""

with gr.Blocks(title="Mwalimu AI Tanzania", css=custom_css, theme=gr.themes.Soft(primary_hue="orange")) as demo:

    gr.HTML("""
    <div class="main-title">
        <h1 style="margin:0; font-size:28px;">🎓 Mwalimu AI Tanzania</h1>
        <p style="margin:6px 0 0; opacity:0.95;">Kidato cha 1 – 6 • Masomo yote • Sauti ya Kweli</p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1, elem_classes="control-card"):
            kidato = gr.Dropdown(
                choices=list(SUBJECTS.keys()),
                value="Kidato cha 1",
                label="📚 Chagua Kidato"
            )
            somo = gr.Dropdown(
                choices=SUBJECTS["Kidato cha 1"],
                value="Hisabati",
                label="📖 Chagua Somo"
            )
            teacher = gr.Dropdown(
                choices=list(TEACHERS.keys()),
                value="Mwalimu Juma",
                label="👨‍🏫 Chagua Mwalimu"
            )

        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                show_label=False,
                avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
            )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Andika swali lako hapa... (mfano: Nifundishe algebra)",
            scale=5,
            show_label=False,
            lines=2
        )
        submit_btn = gr.Button("Tuma ➤", variant="primary", scale=1)

    audio_output = gr.Audio(label="🔊 Sauti ya Mwalimu", autoplay=True)
    clear_btn = gr.Button("🗑️ Anza Upya")

    # Events
    kidato.change(update_subjects, inputs=kidato, outputs=somo)

    submit_btn.click(
        respond,
        inputs=[msg, chatbot, kidato, somo, teacher],
        outputs=[chatbot, audio_output, msg]
    )
    msg.submit(
        respond,
        inputs=[msg, chatbot, kidato, somo, teacher],
        outputs=[chatbot, audio_output, msg]
    )
    clear_btn.click(lambda: ([], None, ""), None, [chatbot, audio_output, msg])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
