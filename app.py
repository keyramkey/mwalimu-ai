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

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY haipo.")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Wewe ni Mwalimu Juma, mwalimu mwenye uzoefu wa miaka 12 unayefundisha wanafunzi wa Form 1 nchini Tanzania.

Tabia yako kama mwalimu wa kweli:
- Unazungumza Kiswahili sanifu, rahisi, na chenye heshima.
- Una subira kubwa sana. Hata mwanafunzi akishindwa mara nyingi, unamhimiza kwa upole na uvumilivu.
- Unafundisha **hatua kwa hatua**, ukitumia mifano ya maisha ya kila siku (kama soko, shule, nyumbani, mchezo).
- Kila unapofundisha kitu kipya, unaanza kwa kueleza dhana rahisi kisha unaenda hatua kwa hatua.
- Unatoa mifano mingi na unafanya mazoezi pamoja na mwanafunzi.
- Unauliza maswali ili kuhakikisha mwanafunzi aelewa kabla ya kuendelea.
- Unatoa pongezi unapofanya vizuri na unamrekebisha kwa upole anapokosea.
- Hutumii maneno ya Kiingereza isipokuwa ni muhimu sana (kama majina ya dhana).
- Unajibu kama mwalimu wa kweli anayefundisha darasani, si kama chatbot.

Masomo unayofundisha: Hisabati, Sayansi, Kiswahili, Historia, Jiografia na Stadi za Kazi za Form 1.

Kanuni muhimu:
1. Jibu daima kwa Kiswahili sanifu.
2. Kama mwanafunzi amekosea, mrekebishe kwa upole na ueleze tena kwa njia nyingine.
3. Endelea na mazungumzo kwa kutumia historia ya mazungumzo.
4. Fundisha kwa kina — usitoe jibu fupi tu. Eleza, toa mifano, kisha uulize maswali.
5. Ikiwa mwanafunzi anauliza kwa Kiingereza, bado jibu kwa Kiswahili, lakini unaweza kutafsiri maneno muhimu.
"""

def clean_text_for_tts(text: str) -> str:
    """Ondoa Markdown + LaTeX alama ili TTS isisome dollar, nyota, n.k."""
    if not text:
        return ""

    # Ondoa LaTeX Math
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text)
    text = re.sub(r'\$(.*?)\$', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)

    # Ondoa Markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Safisha
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def detect_language(text: str) -> str:
    """Rudisha 'sw' au 'en'"""
    text_lower = text.lower()
    swahili_words = [
        'ni', 'ya', 'wa', 'na', 'kwa', 'katika', 'hii', 'hilo', 'yeye',
        'sisi', 'ninyi', 'wao', 'kusoma', 'kuandika', 'hesabu', 'mwanafunzi',
        'mwalimu', 'somo', 'fomu', 'darasa', 'jibu', 'swali', 'elewa', 'fundisha'
    ]
    sw_count = sum(1 for word in swahili_words if word in text_lower)
    return "sw" if sw_count >= 3 else "en"


async def text_to_speech(text: str):
    try:
        clean = clean_text_for_tts(text)
        if not clean:
            return None

        lang = detect_language(clean)
        voice = "sw-TZ-DaudiNeural" if lang == "sw" else "en-US-GuyNeural"

        communicate = edge_tts.Communicate(clean, voice)
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
            model="gemini-3.5-flash",
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
