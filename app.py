import os
import io
import json
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - Hızlı İngilizce Asistanı", 
    page_icon="⚡", 
    layout="wide"
)

# --- GÜVENLİ STREAMLIT SECRETS OKUMA ---
groq_api_key = ""
gemini_api_key = ""

try:
    if "GROQ_API_KEY" in st.secrets:
        groq_api_key = st.secrets["GROQ_API_KEY"]
    if "GEMINI_API_KEY" in st.secrets:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

# --- OTURUM DURUMLARI (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"word": "Swift", "meaning": "Hızlı, çabuk", "example": "A swift response is essential for good communication."},
        {"word": "Instant", "meaning": "Anlık, hemen olan", "example": "Groq provides instant answers."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚡ Hızlı Kontrol")
    manual_groq = st.text_input("Groq API Key", type="password", value="")
    manual_gemini = st.text_input("Gemini API Key", type="password", value="")
    
    if manual_groq: groq_api_key = manual_groq
    if manual_gemini: gemini_api_key = manual_gemini

    st.write(f"Motor: {'Groq (Ultra Hızlı)' if groq_api_key else 'Gemini'}")
    app_mode = st.radio("Mod", ["🗣️ Anlık Sohbet", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviye", ["Beginner", "Intermediate", "Advanced"])

# --- İSTEMCİLER ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

system_prompt = f"You are a friendly English teacher for a {selected_level} student. Keep answers short, natural, correct mistakes gently, and always end with a quick follow-up question."

# ==============================================================================
# MOD 1: ANLIK SOHBET
# ==============================================================================
if app_mode == "🗣️ Anlık Sohbet":
    st.title("⚡ LearnAI: Şimşek Hızında Pratik")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("İngilizce mesajınızı yazın...")

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        ai_response = ""
        success = False

        with st.chat_message("assistant"):
            # Anlık hız hissi için spinner yerine hafif bir akış kullanıyoruz
            messages_payload = [{"role": "system", "content": system_prompt}]
            messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

            # 1. Önce en hızlı model olan Groq 8B Instant ile milisaniyeler içinde yanıt al
            if groq_client and not success:
                try:
                    completion = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages_payload,
                        temperature=0.6,
                        max_tokens=300 # Kısa ve öz yanıtlar hızı artırır
                    )
                    ai_response = completion.choices[0].message.content
                    success = True
                except Exception:
                    pass

            # 2. Groq yoksa Gemini ile devam et
            if gemini_client and not success:
                try:
                    chat_history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    res = gemini_client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=f"{system_prompt}\n\n{chat_history_str}"
                    )
                    ai_response = res.text
                    success = True
                except Exception as e:
                    ai_response = f"Hata: {e}"

            if ai_response:
                st.markdown(ai_response)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})

                # Seslendirmeyi hızlandırmak için hata yakalama ile optimize ettik
                try:
                    tts = gTTS(text=ai_response, lang='en', slow=False)
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    audio_fp.seek(0)
                    st.audio(audio_fp, format="audio/mp3")
                except Exception:
                    pass

# ==============================================================================
# MOD 2: KELİME KARTLARI
# ==============================================================================
elif app_mode == "🎴 Kelime Kartları":
    st.title("🎴 Hızlı Kelime Kartları")
    cards = st.session_state.flashcards
    idx = st.session_state.card_index

    if cards:
        current_card = cards[idx]
        st.info(f"**{current_card['word']}** \n\n *{current_card['example']}*")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👁️ Anlamı"):
                st.success(current_card['meaning'])
        with col2:
            if st.button("➡️ Sonraki"):
                st.session_state.card_index = (idx + 1) % len(cards)
                st.rerun()
