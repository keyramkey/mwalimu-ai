import os
import gradio as gr
from google import genai
from dotenv import load_dotenv
import edge_tts
import asyncio
import tempfile

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY haipo.")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Wewe ni **Mwalimu Juma**, mwalimu mwenye uzoefu wa miaka 12 unayefundisha wanafunzi wa Form 1 nchini Tanzania.

Tabia yako:
- Unazungumza Kiswahili sanifu, rahisi, na chenye heshima.
- Una subira kubwa. Hata mwanafunzi akishindwa mara nyingi, unamhimiza kwa upole.
- Unafundisha hatua kwa hatua, ukitumia mifano ya maisha ya kila siku.
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa.
- Unatoa pongezi unapofanya vizuri.
- Hutumii maneno ya Kiingereza isipokuwa ni muhimu, na unayatafsiri.
- Unajibu kama mwalimu wa kweli, si kama roboti.

Masomo unayofundisha: Hisabati, Sayansi, Kiswahili, Historia, Jiografia na Stadi za Kazi za Form 1.

Kanuni muhimu:
1. Jibu daima kwa Kiswahili sanifu.
2. Kama mwanafunzi amekosea, mrekebishe kwa upole na umpe mifano.
3. Endelea na mazungumzo kwa kutumia historia ya mazungumzo.
"""

async def text_to_speech(text: str):
    try:
        voice = "sw-TZ-DaudiNeural"
        communicate = edge_tts.Communicate(text, voice)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        print(f"TTS Error: {e}")
        return None


def get_ai_response(message: str, history: list) -> str:
    if client is None:
        return "Samahani, API Key haipo. Tafadhali weka GEMINI_API_KEY kwenye Railway Variables."

    try:
        # Support both old and new history formats
        contents = []
        for item in history:
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content", "")
                if role == "user":
                    contents.append({"role": "user", "parts": [{"text": content}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": content}]})
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                user_msg, bot_msg = item
                if user_msg:
                    contents.append({"role": "user", "parts": [{"text": user_msg}]})
                if bot_msg:
                    contents.append({"role": "model", "parts": [{"text": bot_msg}]})

        contents.append({"role": "user", "parts": [{"text": message}]})

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.7,
            }
        )
        return response.text.strip()
    except Exception as e:
        return f"Samahani, nimepata hitilafu. Tafadhali jaribu tena.\n\n(Hitilafu: {str(e)})"


def respond(message, history):
    user_text = (message or "").strip()
    if not user_text:
        return history, None, ""

    bot_response = get_ai_response(user_text, history or [])

    # Use classic tuple format for maximum compatibility
    new_history = (history or []) + [[user_text, bot_response]]

    try:
        audio_path = asyncio.run(text_to_speech(bot_response))
    except Exception:
        audio_path = None

    return new_history, audio_path, ""


# ======================
# PROFESSIONAL UI
# ======================

custom_css = """
.gradio-container {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    max-width: 900px !important;
    margin: 0 auto !important;
}
.main-header {
    text-align: center;
    padding: 24px 16px 12px;
    background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
    border-radius: 16px;
    color: white;
    margin-bottom: 20px;
}
.main-header h1 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 700;
}
.main-header p {
    margin: 8px 0 0;
    opacity: 0.9;
    font-size: 1rem;
}
footer {
    display: none !important;
}
"""

with gr.Blocks(
    title="Mwalimu AI | Mwalimu wa Form 1",
    css=custom_css,
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=["Inter", "system-ui", "sans-serif"]
    )
) as demo:

    gr.HTML("""
    <div class="main-header">
        <h1>🎓 Mwalimu AI</h1>
        <p>Mwalimu wako wa Form 1 • Kiswahili • Subira • Ufahamu</p>
    </div>
    """)

    chatbot = gr.Chatbot(
        label="",
        height=480,
        show_label=False,
        avatar_images=(
            None,
            "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
        ),
        bubble_full_width=False,
        layout="bubble"
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Andika swali lako hapa... mfano: Nifundishe algebra ya Form 1",
            show_label=False,
            scale=5,
            lines=2,
            max_lines=4
        )
        submit_btn = gr.Button("Tuma →", variant="primary", scale=1, min_width=100)

    audio_output = gr.Audio(
        label="🔊 Jibu la Mwalimu",
        autoplay=True,
        visible=True
    )

    with gr.Row():
        clear_btn = gr.Button("🗑️ Anza Upya", variant="secondary")
        gr.Markdown("<small style='text-align:right;opacity:0.6;'>Mwalimu Juma • Form 1 • Tanzania</small>")

    # Events
    submit_btn.click(
        respond,
        inputs=[msg, chatbot],
        outputs=[chatbot, audio_output, msg]
    )
    msg.submit(
        respond,
        inputs=[msg, chatbot],
        outputs=[chatbot, audio_output, msg]
    )
    clear_btn.click(
        lambda: ([], None, ""),
        None,
        [chatbot, audio_output, msg]
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False
    )
