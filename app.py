import os
import io
import json
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - Kesintisiz Sesli İngilizce Pratiği", 
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
        {"word": "Automatic", "meaning": "Otomatik", "example": "The audio plays automatically."},
        {"word": "Seamless", "meaning": "Kusursuz, kesintisiz", "example": "We have a seamless conversation."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

# --- SIDEBAR (KONTROL PANELİ VE GİZLİ API ALANI) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    
    with st.expander("🔑 API Anahtarları (Gizli Ayar)"):
        manual_groq = st.text_input("Groq API Key", type="password", value="")
        manual_gemini = st.text_input("Gemini API Key", type="password", value="")
        
        if manual_groq: groq_api_key = manual_groq
        if manual_gemini: gemini_api_key = manual_gemini

    st.write(f"**Motor Durumu:** {'⚡ Groq Şimşek Mod' if groq_api_key else '💎 Gemini Mod'}")
    
    st.divider()
    app_mode = st.radio("Uygulama Modu", ["🗣️ Canlı Otomatik Sesli Sohbet", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Samimi Arkadaş", "Sabırlı Eğitmen", "Enerjik Koç"])

# --- İSTEMCİLERİ BAŞLATMA ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

system_prompt = f"You are Sarah, a friendly and warm female English AI teacher ({teacher_persona}) talking with a {selected_level} student. Keep your answers short, natural, conversational, correct mistakes gently, and always end with a quick follow-up question to keep the conversation flowing."


# ==============================================================================
# MOD 1: CANLI OTOMATİK SESLİ & YAZILI SOHBET
# ==============================================================================
if app_mode == "🗣️ Canlı Otomatik Sesli Sohbet":
    
    # Üst Bölüm: Kız Avatar (Sarah)
    col_avatar, col_info = st.columns([1, 4])
    with col_avatar:
        st.image(
            "https://encrypted-tbn0.gstatic.com/licensed-image?q=tbn:ANd9GcQaWGvl8gGreJdNp1fy2Nj5NdWiUdFk4bOGeGvgAlZIIpEvY5kkFOoNIG19cUJhye06V1VKgG5QkMaSUSU", 
            width=110, 
            caption="Sarah (AI Teacher)"
        )
    with col_info:
        st.title("🗣️ Sarah ile Kesintisiz Sesli Pratik")
        st.markdown("Merhaba! Aşağıdaki mikrofona konuşarak ya da dilerseniz metin yazarak sohbet edebilirsiniz. Sarah sana cevap verdiğinde **sesi otomatik olarak oynatacak** ve yeni bir şey söylemen için mikrofonu hazır tutacaktır.")

    st.divider()

    # Sohbet Geçmişi
    for msg in st.session_state.messages:
        avatar_icon = "👩‍🏫" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    # Girdi Alanı: Mikrofon ve Metin Alternatifi
    col_mic, col_text = st.columns([2, 1])
    
    user_query = ""

    with col_mic:
        st.write("🎙️ **Sesli Konuşma Alanı:**")
        audio_file_input = st.audio_input("Mikrofonu Başlat / Kaydet")
        
        if audio_file_input is not None and groq_client:
            with st.spinner("Sarah sesini dinliyor..."):
                try:
                    audio_bytes = audio_file_input.getvalue()
                    audio_io = io.BytesIO(audio_bytes)
                    audio_io.name = "speech.wav"

                    transcription = groq_client.audio.transcriptions.create(
                        file=(audio_io.name, audio_io.read()),
                        model="whisper-large-v3",
                        response_format="text",
                        language="en"
                    )
                    user_query = transcription.strip()
                except Exception as e:
                    st.error(f"Ses algılama hatası: {e}")

    with col_text:
        st.write("⌨️ **Veya Yazarak Gönder:**")
        text_query = st.chat_input("Mesajınızı buraya yazın...")
        if text_query:
            user_query = text_query

    # Kullanıcı mesajı geldiyse işleme al
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

                # 1. Groq Hızlı Model
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

                # 2. Gemini Yedek Model
                if gemini_client and not success:
                    try:
                        chat_history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                        res = gemini_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"{system_prompt}\n\n{chat_history_str}"
                        )
                        ai_response = res.text
                        success = True
                    except Exception as e:
                        ai_response = f"Bağlantı kurulamadı: {e}"

                if ai_response:
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

                    # OTOMATİK SESLENDİRME (autoplay=True parametresi ile tuşa basmadan çalma)
                    try:
                        tts = gTTS(text=ai_response, lang='en', slow=False)
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        audio_fp.seek(0)
                        
                        # Tarayıcıda otomatik ses oynatma tetiklemesi
                        st.audio(audio_fp, format="audio/mp3", autoplay=True)
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
