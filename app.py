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
Wewe ni Mwalimu Juma, mwalimu mwenye uzoefu wa miaka 12 unayefundisha wanafunzi wa Form 1 nchini Tanzania.

Tabia yako:
- Unazungumza Kiswahili sanifu, rahisi, na chenye heshima.
- Una subira kubwa. Hata mwanafunzi akishindwa mara nyingi, unamhimiza kwa upole.
- Unafundisha hatua kwa hatua, ukitumia mifano ya maisha ya kila siku.
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa.
- Unatoa pongezi unapofanya vizuri.
- Hutumii maneno ya Kiingereza isipokuwa ni muhimu.
- Unajibu kama mwalimu wa kweli.

Masomo: Hisabati, Sayansi, Kiswahili, Historia, Jiografia na Stadi za Kazi za Form 1.

Kanuni:
1. Jibu daima kwa Kiswahili sanifu.
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
        for item in (history or []):
            if isinstance(item, dict) and "role" in item and "content" in item:
                role = item["role"]
                text = item["content"]
                if role == "user":
                    contents.append({"role": "user", "parts": [{"text": str(text)}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": str(text)}]})

        contents.append({"role": "user", "parts": [{"text": message}]})

        response = client.models.generate_content(
            model="gemini-3.5-flash",          # ← Model inayopatikana muda mwingi
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.7,
            }
        )
        return response.text.strip()
    except Exception as e:
        return f"Samahani, nimepata hitilafu. Tafadhali jaribu tena.\n\n({str(e)})"


def respond(message, history):
    user_text = (message or "").strip()
    if not user_text:
        return history, None, ""

    bot_response = get_ai_response(user_text, history)

    new_history = (history or []) + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": bot_response}
    ]

    try:
        audio_path = asyncio.run(text_to_speech(bot_response))
    except Exception:
        audio_path = None

    return new_history, audio_path, ""


with gr.Blocks(title="Mwalimu AI - Form 1") as demo:

    gr.Markdown("""
    # 🎓 Mwalimu AI
    **Mwalimu Juma** • Form 1 • Kiswahili
    
    Karibu! Ninaweza kukufundisha Hisabati, Sayansi, Kiswahili na masomo mengine.
    """)

    chatbot = gr.Chatbot(
        height=450,
        avatar_images=(None, "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
    )

    with gr.Row():
        msg = gr.Textbox(
            placeholder="Andika swali lako hapa... mfano: Nifundishe algebra ya Form 1",
            scale=5,
            lines=2,
            show_label=False
        )
        submit_btn = gr.Button("Tuma", variant="primary", scale=1)

    audio_output = gr.Audio(label="Jibu la Mwalimu (Sauti)", autoplay=True)
    clear_btn = gr.Button("Anza Upya")

    submit_btn.click(respond, inputs=[msg, chatbot], outputs=[chatbot, audio_output, msg])
    msg.submit(respond, inputs=[msg, chatbot], outputs=[chatbot, audio_output, msg])
    clear_btn.click(lambda: ([], None, ""), None, [chatbot, audio_output, msg])

    gr.Markdown("---\n*Mwalimu Juma • Form 1 • Tanzania*")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False
    )
