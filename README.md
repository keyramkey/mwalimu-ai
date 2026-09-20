# Mwalimu AI - Mwalimu wa Form 1 kwa Kiswahili

AI Mwalimu anayefundisha wanafunzi wa Form 1 kwa **Kiswahili kizuri**, kwa sauti, na kwa tabia ya mwalimu wa kweli.

## Vipengele
- Full Voice (mwanafunzi anaongea, AI inasikiliza na kujibu kwa sauti)
- Kiswahili sanifu na rahisi kuelewa
- Memory ya mazungumzo
- Tabia ya mwalimu mwenye subira na motisha
- Masomo ya Form 1 (Hisabati, Sayansi, Kiswahili, Historia, Jiografia n.k.)

## Jinsi ya Kuendesha Locally

1. Fungua terminal ndani ya folder hii
2. Tengeneza virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   # au venv\Scripts\activate  # Windows
   ```
3. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Nakili `.env.example` kuwa `.env` na weka Gemini API Key yako:
   ```bash
   cp .env.example .env
   ```
5. Endesha app:
   ```bash
   python app.py
   ```

## Deploy kwenye Railway

1. Push code yote kwenye GitHub
2. Nenda Railway → New Project → Deploy from GitHub
3. Ongeza Variable: `GEMINI_API_KEY`
4. Deploy

## Gemini API Key (Bure)
Pata hapa: https://aistudio.google.com/app/apikey
