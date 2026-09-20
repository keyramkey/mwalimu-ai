import os
import gradio as gr
from google import genai
from dotenv import load_dotenv
import edge_tts
import asyncio
import tempfile

load_dotenv()

# ======================
# CONFIGURATION
# ======================
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
- Una subira kubwa. Hata mwanafunzi akishindwa mara nyingi, unamhimiza.
- Unafundisha hatua kwa hatua.
- Unatumia mifano ya maisha ya kila siku ya Tanzania.
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa.
- Unatoa pongezi unapofanya vizuri.
- Hutoshei maneno ya Kiingereza isipokuwa ni muhimu sana.
- Unajibu kama mwalimu wa kweli.

Masomo: Hisabati, Sayansi, Kiswahili, Historia, Jiografia na Stadi za Kazi.

Kanuni:
1. Jibu daima kwa Kiswahili.
2. Kama mwanafunzi amekosea, mrekebishe kwa upole.
3. Endelea na mazungumzo kwa kutumia historia.
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
        return "Samahani, API Key haipo. Weka GEMINI_API_KEY kwenye Railway Variables."

    try:
        contents = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

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
        return f"Samahani, nimepata hitilafu. (Hitilafu: {str(e)})"


def respond(message, history):
    user_text = (message or "").strip()
    if not user_text:
        return history, None, ""

    bot_response = get_ai_response(user_text, history or [])

    # New Gradio messages format
    new_history = (history or []) + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": bot_response}
    ]

    try:
        audio_path = asyncio.run(text_to_speech(bot_response))
    except Exception:
        audio_path = None

    return new_history, audio_path, ""


# ======================
# GRADIO INTERFACE
# ======================

with gr.Blocks(title="Mwalimu AI - Form 1") as demo:

    gr.Markdown("""
    # 🎓 Mwalimu AI — Mwalimu wako wa Form 1
    **Karibu!** Mimi ni **Mwalimu Juma**. Ninaweza kukufundisha Hisabati, Sayansi, Kiswahili na masomo mengine kwa Kiswahili.
    """)

    chatbot = gr.Chatbot(
        label="Mazungumzo na Mwalimu",
        height=420,
        type="messages",
        avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Andika swali lako hapa... mfano: Nifundishe algebra ya Form 1",
            label="Ujumbe wako",
            scale=4,
            lines=2
        )
        submit_btn = gr.Button("Tuma", variant="primary", scale=1)

    audio_output = gr.Audio(label="Jibu la Mwalimu (Sauti)", autoplay=True)
    clear_btn = gr.Button("Anza Upya")

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

    clear_btn.click(lambda: ([], None, ""), None, [chatbot, audio_output, msg])

    gr.Markdown("---\n**Andika swali kwa Kiswahili. Mwalimu atajibu kwa maandishi + sauti.**")

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 8080)),
        share=False
    )
