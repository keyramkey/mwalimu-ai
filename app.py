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
# DATA
# ======================
SUBJECTS = {
    "Kidato cha 1": ["Hisabati", "Kiswahili", "English Language", "Biology", "Geography", "History", "Civics", "Physics", "Chemistry", "Agriculture"],
    "Kidato cha 2": ["Hisabati", "Kiswahili", "English Language", "Biology", "Geography", "History", "Civics", "Physics", "Chemistry", "Agriculture"],
    "Kidato cha 3": ["Hisabati", "Kiswahili", "English Language", "Biology", "Geography", "History", "Civics", "Physics", "Chemistry", "Agriculture", "Computer Science", "Business Studies"],
    "Kidato cha 4": ["Hisabati", "Kiswahili", "English Language", "Biology", "Geography", "History", "Civics", "Physics", "Chemistry", "Agriculture", "Computer Science", "Business Studies", "Additional Mathematics"],
    "Kidato cha 5": ["Advanced Mathematics", "Physics", "Chemistry", "Biology", "Geography", "History", "Economics", "Accountancy", "Kiswahili", "English Language", "Literature in English"],
    "Kidato cha 6": ["Advanced Mathematics", "Physics", "Chemistry", "Biology", "Geography", "History", "Economics", "Accountancy", "Kiswahili", "English Language", "Literature in English"]
}

TEACHERS = {
    "Mwalimu Juma": {"voice": "sw-TZ-DaudiNeural", "lang": "sw"},
    "Bi. Amina": {"voice": "sw-TZ-ZuriNeural", "lang": "sw"},
    "Mr. John": {"voice": "en-US-GuyNeural", "lang": "en"},
    "Ms. Sarah": {"voice": "en-US-JennyNeural", "lang": "en"},
}

def get_system_prompt(kidato, somo, teacher):
    if TEACHERS[teacher]["lang"] == "en":
        return f"You are {teacher}, a Form {kidato[-1]} teacher in Tanzania teaching {somo}. Teach step by step with simple examples. Be patient and clear."
    return f"Wewe ni {teacher}, mwalimu wa {kidato} unayefundisha {somo}. Fundisha hatua kwa hatua kwa Kiswahili sanifu, toa mifano, na uulize maswali."

def clean_text_for_tts(text):
    if not text: return ""
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
    text = re.sub(r'\b([xX])\b', 'eks', text)
    text = re.sub(r'\b([yY])\b', 'wai', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

async def text_to_speech(text, voice):
    try:
        clean = clean_text_for_tts(text)
        if not clean: return None
        communicate = edge_tts.Communicate(clean, voice, rate="+8%")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        print("TTS Error:", e)
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
            config={"system_instruction": get_system_prompt(kidato, somo, teacher), "temperature": 0.65}
        )
        return response.text.strip()
    except Exception as e:
        return f"Samahani, nimepata hitilafu.\n({str(e)})"

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
# CSS MPYA KABISA (Haifanani na Gradio)
# ======================
custom_css = """
/* Ficha footer ya Gradio */
footer {display: none !important;}
.gradio-container {max-width: 980px !important; margin: 0 auto !important; padding: 20px !important; background: #f8fafc !important;}

/* Header */
.app-header {
    background: linear-gradient(135deg, #0f766e, #0d9488, #f97316);
    color: white;
    padding: 22px 28px;
    border-radius: 20px;
    margin-bottom: 24px;
    box-shadow: 0 10px 25px rgba(15, 118, 110, 0.25);
    text-align: center;
}
.app-header h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
}
.app-header p {
    margin: 6px 0 0;
    opacity: 0.92;
    font-size: 15px;
}

/* Cards */
.control-card {
    background: white;
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
}
.chat-card {
    background: white;
    border-radius: 18px;
    padding: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
}

/* Chatbot */
#chatbot {
    height: 440px !important;
    border: none !important;
    background: #f8fafc !important;
    border-radius: 14px !important;
}

/* Buttons */
button.primary {
    background: linear-gradient(135deg, #f97316, #ea580c) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3) !important;
}
button.primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(249, 115, 22, 0.4) !important;
}

/* Inputs */
.gr-textbox textarea, .gr-dropdown {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
}
"""

with gr.Blocks(css=custom_css, title="Mwalimu AI Tanzania") as demo:

    # Header mpya
    gr.HTML("""
    <div class="app-header">
        <h1>🎓 Mwalimu AI Tanzania</h1>
        <p>Kidato cha 1 – 6 • Masomo yote • Sauti ya Kweli</p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1, elem_classes="control-card"):
            gr.Markdown("### ⚙️ Chagua")
            kidato = gr.Dropdown(choices=list(SUBJECTS.keys()), value="Kidato cha 1", label="📚 Kidato")
            somo = gr.Dropdown(choices=SUBJECTS["Kidato cha 1"], value="Hisabati", label="📖 Somo")
            teacher = gr.Dropdown(choices=list(TEACHERS.keys()), value="Mwalimu Juma", label="👨‍🏫 Mwalimu")

        with gr.Column(scale=2, elem_classes="chat-card"):
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                show_label=False,
                avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
            )

    with gr.Row():
        msg = gr.Textbox(placeholder="Andika swali lako hapa...", scale=5, show_label=False, lines=2)
        submit_btn = gr.Button("Tuma ➤", variant="primary", scale=1)

    audio_output = gr.Audio(label="🔊 Sauti ya Mwalimu", autoplay=True)
    clear_btn = gr.Button("🗑️ Anza Upya", variant="secondary")

    # Events
    kidato.change(update_subjects, inputs=kidato, outputs=somo)
    submit_btn.click(respond, inputs=[msg, chatbot, kidato, somo, teacher], outputs=[chatbot, audio_output, msg])
    msg.submit(respond, inputs=[msg, chatbot, kidato, somo, teacher], outputs=[chatbot, audio_output, msg])
    clear_btn.click(lambda: ([], None, ""), None, [chatbot, audio_output, msg])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_api=False,
        footer=None
    )
