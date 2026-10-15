import os
import io
import json
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - Yapay Zeka İngilizce Koçu", 
    page_icon="👩‍🏫", 
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
        {"word": "Interactive", "meaning": "Etkileşimli", "example": "Interactive learning helps you speak faster."},
        {"word": "Confident", "meaning": "Kendinden emin", "example": "Practice every day to feel more confident."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

# --- SIDEBAR (KONTROL PANELİ VE GİZLİ API ALANI) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    
    # API anahtarları tamamen gizli bir expander içerisine alındı
    with st.expander("🔑 API Anahtarları (Gizli Ayar)"):
        manual_groq = st.text_input("Groq API Key", type="password", value="")
        manual_gemini = st.text_input("Gemini API Key", type="password", value="")
        
        if manual_groq: groq_api_key = manual_groq
        if manual_gemini: gemini_api_key = manual_gemini

    st.write(f"**Motor Durumu:** {'⚡ Groq Hızlı Mod' if groq_api_key else '💎 Gemini Mod'}")
    
    st.divider()
    app_mode = st.radio("Uygulama Modu", ["🗣️ Canlı Sesli & Yazılı Sohbet", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Samimi Arkadaş", "Sabırlı Eğitmen", "Enerjik Koç"])

# --- İSTEMCİLERİ BAŞLATMA ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

system_prompt = f"You are Sarah, a friendly and warm female English AI teacher ({teacher_persona}) talking with a {selected_level} student. Keep your answers short, natural, conversational, correct mistakes gently, and always end with a quick follow-up question to keep the chat going."


# ==============================================================================
# MOD 1: CANLI SESLİ & YAZILI SOHBET (AVATAR DESTEKLİ)
# ==============================================================================
if app_mode == "🗣️ Canlı Sesli & Yazılı Sohbet":
    
    # Üst Bölüm: Kız Avatar ve Karşılama Alanı
    col_avatar, col_info = st.columns([1, 4])
    with col_avatar:
        st.image(
            "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcR8UQD4V16SP0lsoSEj1c5U_aPRrMdZHTUNppIZFvUQqevnKw0mJ3WdN6slLVVi_j1tbW6CDuMrAMAD_Lo", 
            width=110, 
            caption="Sarah (AI Teacher)"
        )
    with col_info:
        st.title("🗣️ Sarah ile Canlı İngilizce Pratiği")
        st.markdown("Merhaba! Ben Sarah. İster klavyeden yazarak ister mikrofonu kullanarak benimle İngilizce konuşabilir, anında sesli ve yazılı yanıtlar alabilirsin.")

    st.divider()

    # Sohbet Geçmişini Ekrana Bas
    for msg in st.session_state.messages:
        avatar_icon = "👩‍🏫" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # Girdi Seçimi (Mikrofon veya Metin)
    input_choice = st.radio("İletişim Yöntemi Seçin:", ["⌨️ Yazı Yazarak Mesaj Gönder", "🎙️ Mikrofon ile Sesli Konuş"], horizontal=True)
    
    user_query = ""

    if input_choice == "⌨️ Yazı Yazarak Mesaj Gönder":
        user_query = st.chat_input("İngilizce mesajınızı buraya yazın...")
    else:
        st.write("🎙️ **Sesli Mesaj Kaydı:** (Mikrofon tuşuna basın, konuşun ve bitince durdurun)")
        audio_file_input = st.audio_input("Mikrofonu Başlat")
        
        if audio_file_input is not None and groq_client:
            with st.spinner("Sesiniz Sarah tarafından dinleniyor (Whisper STT)..."):
                try:
                    audio_bytes = audio_file_input.getvalue()
                    audio_io = io.BytesIO(audio_bytes)
                    audio_io.name = "speech.wav"

                    # Groq Whisper ile sesi anında metne dök
                    transcription = groq_client.audio.transcriptions.create(
                        file=(audio_io.name, audio_io.read()),
                        model="whisper-large-v3",
                        response_format="text",
                        language="en"
                    )
                    user_query = transcription.strip()
                except Exception as e:
                    st.error(f"Ses algılama hatası: {e}")

    # Kullanıcıdan mesaj veya ses gelmişse işleme al
    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)

        ai_response = ""
        success = False

        with st.chat_message("assistant", avatar="👩‍🏫"):
            with st.spinner("Sarah düşünüyor..."):
                messages_payload = [{"role": "system", "content": system_prompt}]
                messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                # 1. Groq Hızlı Model Denemesi
                if groq_client and not success:
                    try:
                        completion = groq_client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=messages_payload,
                            temperature=0.7,
                            max_tokens=300
                        )
                        ai_response = completion.choices[0].message.content
                        success = True
                    except Exception:
                        pass

                # 2. Gemini Yedek Motor Denemesi
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
                        ai_response = f"Üzgünüm, şu an bağlantı kuramadım: {e}"

                if ai_response:
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

                    # Sarah'nın sesli yanıtını oynat
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
    st.title("🎴 Sarah ile Kelime Pratiği")
    cards = st.session_state.flashcards
    idx = st.session_state.card_index

    if cards:
        current_card = cards[idx]
        st.info(f"**Kelime:** {current_card['word']} \n\n *Örnek Cümle:* {current_card['example']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👁️ Türkçe Anlamı"):
                st.success(f"Anlamı: {current_card['meaning']}")
        with col2:
            if st.button("➡️ Sonraki Kelime"):
                st.session_state.card_index = (idx + 1) % len(cards)
                st.rerun()
