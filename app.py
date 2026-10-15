import os
import io
import json
import time
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - Modern Sesli İngilizce Asistanı", 
    page_icon="✨", 
    layout="wide"
)

# --- MODERN CSS TASARIM DOKUNUŞLARI ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        opacity: 0.95;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px -1px rgba(0, 0, 0, 0.2);
    }
    .sidebar .sidebar-content {
        background-color: #1e293b;
    }
    </style>
""", unsafe_allow_html=True)

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
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Sarah, your AI English teacher. How are you doing today? Let's practice speaking!"}
    ]

if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"word": "Modern", "meaning": "Modern, çağdaş", "example": "This app has a modern design."},
        {"word": "Fluent", "meaning": "Akıcı", "example": "She speaks English fluently."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

# --- SIDEBAR (KONTROL PANELİ) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    
    with st.expander("🔑 API Anahtarları (Gizli Ayar)"):
        manual_groq = st.text_input("Groq API Key", type="password", value="")
        manual_gemini = st.text_input("Gemini API Key", type="password", value="")
        
        if manual_groq: groq_api_key = manual_groq
        if manual_gemini: gemini_api_key = manual_gemini

    st.write(f"**Öncelikli Motor:** {'⚡ Groq (Yedek: Gemini)' if groq_api_key else '💎 Gemini Mod'}")
    
    st.divider()
    app_mode = st.radio("Mod Seçimi", ["🗣️ Canlı Sesli Sohbet", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Samimi Arkadaş", "Sabırlı Eğitmen", "Enerjik Koç"])

# --- İSTEMCİLERİ BAŞLATMA ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

system_prompt = f"You are Sarah, a friendly and warm female English AI teacher ({teacher_persona}) talking with a {selected_level} student. Keep your answers short, natural, conversational, correct mistakes gently, and always end with a quick follow-up question to keep the conversation flowing."


# ==============================================================================
# MOD 1: CANLI SESLİ & YAZILI SOHBET (AKIŞSAL MİKROFON + HATA TOLERANSLI)
# ==============================================================================
if app_mode == "🗣️ Canlı Sesli Sohbet":
    
    # Üst Bilgi ve Avatar
    col_avatar, col_info = st.columns([1, 5])
    with col_avatar:
        st.image(
            "https://static.vecteezy.com/system/resources/previews/060/362/634/non_2x/cartoon-female-teacher-avatar-with-glasses-isolated-in-a-bright-friendly-setting-3d-cartoon-female-teacher-educator-avatar-isolated-on-transparent-background-free-png.png", 
            width=100
        )
    with col_info:
        st.markdown("### Sarah (AI English Teacher)")
        st.caption("Sarah ile sesli veya yazılı olarak pratik yapın. Sunucu yoğunluğu yaşandığında sistem otomatik olarak yedek motora geçer.")

    st.divider()

    # Sohbet Geçmişini Göster
    for msg in st.session_state.messages:
        avatar_icon = "👩‍🏫" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    user_query = ""

    # SOHBET AKIŞININ DEVAMINDA SES KAYIT VE METİN GİRİŞİ
    st.markdown("---")
    st.markdown("🎙️ **Cevabınızı sesli kaydedin veya yazın:**")
    
    col_mic, col_txt = st.columns([1, 1])
    
    with col_mic:
        audio_file_input = st.audio_input("Konuşmak için tıklayın")
        if audio_file_input is not None and groq_client:
            with st.spinner("Sarah sesinizi dinliyor..."):
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
                    st.warning(f"Groq Whisper yoğunluk yaşadı, alternatif işleniyor... ({e})")

    with col_txt:
        text_query = st.chat_input("Veya buraya yazıp gönderin...")
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

                # 1. ÖNCE GROQ DENEMESİ (503 VE YOĞUNLUK HATA TOLERANSLI)
                if groq_client and not success:
                    for attempt in range(2):  # 503 alması durumunda 1 kere kısa bekleme ile tekrar dener
                        try:
                            completion = groq_client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=messages_payload,
                                temperature=0.7,
                                max_tokens=300
                            )
                            ai_response = completion.choices[0].message.content
                            success = True
                            break
                        except Exception as e:
                            time.sleep(0.5)

                # 2. GROQ 503/BAĞLANTI HATASI VERİRSE OTOMATİK GEMINI DEVREYE GİRER
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
                        st.error(f"Yapay zeka servisleri geçici olarak yoğun. Lütfen tekrar deneyin: {e}")

                if ai_response:
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

                    # Otomatik Seslendirme (Autoplay)
                    try:
                        tts = gTTS(text=ai_response, lang='en', slow=False)
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        audio_fp.seek(0)
                        st.audio(audio_fp, format="audio/mp3", autoplay=True)
                    except Exception:
                        pass
                    
                    st.rerun()


# ==============================================================================
# MOD 2: KELİME KARTLARI
# ==============================================================================
elif app_mode == "🎴 Kelime Kartları":
    st.title("🎴 Sarah ile Modern Kelime Kartları")
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
