import os
import gradio as gr
import google.generativeai as genai
from dotenv import load_dotenv
import edge_tts
import asyncio
import tempfile
import uuid

load_dotenv()

# ======================
# CONFIGURATION
# ======================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY haipo. Weka kwenye faili .env")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Model
model = genai.GenerativeModel("gemini-2.0-flash")

# System Prompt - Mwalimu wa Form 1
SYSTEM_PROMPT = """
Wewe ni **Mwalimu Juma**, mwalimu mwenye uzoefu wa miaka 12 unayefundisha wanafunzi wa Form 1 nchini Tanzania.

Tabia yako:
- Unazungumza Kiswahili sanifu, rahisi, na chenye heshima.
- Una subira kubwa. Hata mwanafunzi akishindwa mara nyingi, unamhimiza.
- Unafundisha hatua kwa hatua.
- Unatumia mifano ya maisha ya kila siku ya Tanzania (shule, soko, nyumbani, michezo n.k.).
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa.
- Unatoa pongezi unapofanya vizuri.
- Hutoshei maneno ya Kiingereza isipokuwa ni muhimu sana (na unayatafsiri).
- Unajibu kama mwalimu wa kweli, si kama roboti.

Masomo unayofundisha:
- Hisabati (Algebra, Geometry, Namba n.k.)
- Sayansi (Fizikia, Kemia, Biolojia ya Form 1)
- Kiswahili
- Historia
- Jiografia
- Stadi za Kazi na Maisha

Kanuni:
1. Jibu daima kwa Kiswahili.
2. Kama mwanafunzi amekosea, mrekebishe kwa upole.
3. Kama swali ni nje ya mtaala wa Form 1, mwambie kwa upole na umrudishe kwenye mada.
4. Endelea na mazungumzo kwa kutumia historia ya mazungumzo.
"""

# ======================
# HELPER FUNCTIONS
# ======================

async def text_to_speech(text: str) -> str:
    """Convert text to speech using edge-tts (Swahili voice)"""
    try:
        # Swahili voice from Microsoft Edge
        voice = "sw-TZ-DaudiNeural"  # Male voice - Tanzania
        # Alternative: "sw-TZ-RehemaNeural" (Female)
        
        communicate = edge_tts.Communicate(text, voice)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        await communicate.save(temp_file.name)
        return temp_file.name
    except Exception as e:
        print(f"TTS Error: {e}")
        return None


def get_ai_response(message: str, history: list) -> str:
    """Get response from Gemini with conversation history"""
    try:
        # Build conversation
        chat_history = []
        for human, ai in history:
            if human:
                chat_history.append({"role": "user", "parts": [human]})
            if ai:
                chat_history.append({"role": "model", "parts": [ai]})

        chat = model.start_chat(history=chat_history)
        
        full_prompt = f"{SYSTEM_PROMPT}\n\nMwanafunzi amesema: {message}"
        response = chat.send_message(full_prompt)
        
        return response.text.strip()
    except Exception as e:
        return f"Samahani, nimepata hitilafu. Tafadhali jaribu tena. (Hitilafu: {str(e)})"


# ======================
# GRADIO INTERFACE
# ======================

def respond(message, history, audio_input):
    """
    Main response function
    - message: text from user
    - history: conversation history
    - audio_input: recorded audio (if any)
    """
    
    user_text = message.strip() if message else ""
    
    # TODO: Later we will add real Speech-to-Text here
    # Kwa sasa tunaanza na text. Voice input tutaiongeza hatua inayofuata.
    
    if not user_text:
        return history, None, "Tafadhali andika swali au ujumbe wako."
    
    # Get AI response
    bot_response = get_ai_response(user_text, history)
    
    # Update history
    history = history + [[user_text, bot_response]]
    
    # Generate speech
    audio_path = asyncio.run(text_to_speech(bot_response))
    
    return history, audio_path, ""


# Custom CSS for better look
css = """
.gradio-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.chatbot {
    height: 450px !important;
}
"""

with gr.Blocks(title="Mwalimu AI - Form 1", css=css, theme=gr.themes.Soft()) as demo:
    
    gr.Markdown("""
    # 🎓 Mwalimu AI — Mwalimu wako wa Form 1
    **Karibu!** Mimi ni Mwalimu Juma. Ninaweza kukufundisha Hisabati, Sayansi, Kiswahili na masomo mengine kwa Kiswahili.
    
    Andika swali lako hapa chini. (Sauti kamili inaongezwa hatua kwa hatua)
    """)
    
    chatbot = gr.Chatbot(
        label="Mazungumzo na Mwalimu",
        height=420,
        show_copy_button=True,
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
    
    # Event handlers
    submit_btn.click(
        respond,
        inputs=[msg, chatbot, gr.State(None)],
        outputs=[chatbot, audio_output, msg]
    )
    
    msg.submit(
        respond,
        inputs=[msg, chatbot, gr.State(None)],
        outputs=[chatbot, audio_output, msg]
    )
    
    clear_btn.click(lambda: ([], None, ""), None, [chatbot, audio_output, msg])
    
    gr.Markdown("""
    ---
    **Maelekezo:**  
    - Andika swali kwa Kiswahili  
    - Mwalimu atajibu kwa maandishi + sauti  
    - Full voice (kuongea) inaongezwa hivi karibuni
    """)

# ======================
# RUN
# ======================
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 7860)),
        share=False
    )
