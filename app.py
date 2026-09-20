import os
import re
import gradio as gr
from google import genai
from dotenv import load_dotenv
import edge_tts
import asyncio
import tempfile
from datetime import datetime

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ======================
# WALIMU (Sauti tofauti)
# ======================
TEACHERS = {
    "Mwalimu Juma (Mwanaume - Kiswahili)": {
        "voice": "sw-TZ-DaudiNeural",
        "prompt_name": "Mwalimu Juma",
        "style": "mwalimu mwenye uzoefu, subira, anayefundisha hatua kwa hatua"
    },
    "Bi. Amina (Mwanamke - Kiswahili)": {
        "voice": "sw-TZ-ZuriNeural",
        "prompt_name": "Bi. Amina",
        "style": "mwalimu mwanamke mwenye upole, anayehimiza sana na kutoa mifano ya kila siku"
    },
    "Mr. John (Mwanaume - English)": {
        "voice": "en-US-GuyNeural",
        "prompt_name": "Mr. John",
        "style": "patient English teacher who explains step by step with simple examples"
    },
    "Ms. Sarah (Mwanamke - English)": {
        "voice": "en-US-JennyNeural",
        "prompt_name": "Ms. Sarah",
        "style": "friendly and clear English teacher who checks understanding often"
    }
}

def get_system_prompt(teacher_name: str) -> str:
    t = TEACHERS[teacher_name]
    if "English" in teacher_name:
        return f"""
You are {t['prompt_name']}, a Form 1 teacher in Tanzania.
Style: {t['style']}.
- Speak simple, clear English.
- Teach step by step with everyday examples.
- Always check if the student understands.
- Be patient and encouraging.
- Give quizzes when appropriate.
"""
    else:
        return f"""
Wewe ni {t['prompt_name']}, mwalimu wa Form 1 nchini Tanzania.
Tabia: {t['style']}.
- Unazungumza Kiswahili sanifu na rahisi.
- Unafundisha hatua kwa hatua kwa mifano ya maisha ya kila siku.
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa.
- Unatoa pongezi na unamrekebisha kwa upole.
- Unapenda kutoa quiz fupi baada ya kufundisha.
"""

# ======================
# SAFISHA MAANDISHI KWA TTS
# ======================
def clean_text_for_tts(text: str) -> str:
    if not text:
        return ""

    # Ondoa LaTeX
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)

    # Ondoa Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Badilisha herufi za hesabu ili zisomeke vizuri
    text = re.sub(r'\b([xy])\b', lambda m: {"x": "eks", "y": "wai"}[m.group(1)], text, flags=re.IGNORECASE)
    text = re.sub(r'\b([a-z])\b', lambda m: m.group(1).upper(), text)  # herufi moja → capital

    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


async def text_to_speech(text: str, voice: str):
    try:
        clean = clean_text_for_tts(text)
        if not clean:
            return None
        communicate = edge_tts.Communicate(clean, voice, rate="+10%")  # haraka kidogo
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        print(f"TTS Error: {e}")
        return None


def get_ai_response(message: str, history: list, teacher: str) -> str:
    if client is None:
        return "Samahani, API Key haipo."

    try:
        contents = []
        for item in (history or []):
            if isinstance(item, dict) and "role" in item and "content" in item:
                role = "user" if item["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": str(item["content"])}]})

        contents.append({"role": "user", "parts": [{"text": message}]})

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config={
                "system_instruction": get_system_prompt(teacher),
                "temperature": 0.65,
            }
        )
        return response.text.strip()
    except Exception as e:
        return f"Samahani, nimepata hitilafu. Jaribu tena.\n\n({str(e)})"


# ======================
# QUIZ STATE
# ======================
quiz_state = {
    "active": False,
    "questions": [],
    "current": 0,
    "score": 0,
    "answers": []
}


def respond(message, history, teacher):
    user_text = (message or "").strip()
    if not user_text:
        return history, None, "", gr.update()

    bot_response = get_ai_response(user_text, history, teacher)

    new_history = (history or []) + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": bot_response}
    ]

    voice = TEACHERS[teacher]["voice"]
    try:
        audio_path = asyncio.run(text_to_speech(bot_response, voice))
    except:
        audio_path = None

    return new_history, audio_path, "", gr.update(visible=False)


def start_quiz(topic, teacher):
    if not topic.strip():
        return "Tafadhali andika mada ya quiz (mfano: Algebra, Fractions, Photosynthesis)", gr.update(visible=False), None

    prompt = f"""
Tengeneza quiz fupi ya Form 1 juu ya: {topic}
Toa maswali 4 tu ya multiple choice.
Kila swali liwe na chaguo A B C D.
Andika kwa format hii tu:

SWALI 1: ...
A) ...
B) ...
C) ...
D) ...
JIBU: A

SWALI 2: ...
...
"""
    raw = get_ai_response(prompt, [], teacher)
    
    # Parse simple (for demo)
    quiz_state["active"] = True
    quiz_state["questions"] = [raw]   # simplified for now
    quiz_state["current"] = 0
    quiz_state["score"] = 0

    return raw, gr.update(visible=True), None


# ======================
# UI BORA
# ======================
with gr.Blocks(
    title="Mwalimu AI - Form 1",
    theme=gr.themes.Soft(primary_hue="orange", secondary_hue="blue"),
    css="""
    .gradio-container { max-width: 950px !important; }
    #chatbot { height: 480px !important; }
    """
) as demo:

    gr.Markdown("""
    # 🎓 Mwalimu AI - Form 1
    **Chagua mwalimu wako → Anza kujifunza au fanya Quiz**
    """)

    with gr.Row():
        teacher_dd = gr.Dropdown(
            choices=list(TEACHERS.keys()),
            value="Mwalimu Juma (Mwanaume - Kiswahili)",
            label="👨‍🏫 Chagua Mwalimu",
            scale=2
        )

    with gr.Tabs():
        with gr.Tab("💬 Mazungumzo"):
            chatbot = gr.Chatbot(
                elem_id="chatbot",
                avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"),
                show_label=False
            )
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Andika swali lako hapa...",
                    scale=5,
                    show_label=False,
                    lines=2
                )
                submit_btn = gr.Button("Tuma", variant="primary", scale=1)

            audio_output = gr.Audio(label="Sauti ya Mwalimu", autoplay=True)
            clear_btn = gr.Button("🗑️ Anza Upya")

        with gr.Tab("📝 Quiz"):
            gr.Markdown("### Fanya Quiz fupi")
            quiz_topic = gr.Textbox(label="Andika mada ya Quiz", placeholder="mfano: Algebra, Fractions, Photosynthesis...")
            start_quiz_btn = gr.Button("Anza Quiz", variant="primary")
            quiz_output = gr.Markdown()
            quiz_audio = gr.Audio(autoplay=True)
            quiz_choices = gr.Radio(
                choices=["A", "B", "C", "D"],
                label="Chagua jibu lako",
                visible=False
            )

    # Events
    submit_btn.click(
        respond,
        inputs=[msg, chatbot, teacher_dd],
        outputs=[chatbot, audio_output, msg, quiz_choices]
    )
    msg.submit(
        respond,
        inputs=[msg, chatbot, teacher_dd],
        outputs=[chatbot, audio_output, msg, quiz_choices]
    )
    clear_btn.click(lambda: ([], None, ""), None, [chatbot, audio_output, msg])

    start_quiz_btn.click(
        start_quiz,
        inputs=[quiz_topic, teacher_dd],
        outputs=[quiz_output, quiz_choices, quiz_audio]
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
