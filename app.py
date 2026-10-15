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
    page_title="LearnAI - Çoklu API Destekli Sesli İngilizce Asistanı", 
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

# --- ÇOKLU API ANAHTARI YÖNETİMİ ---
# secrets.toml içinde virgülle ayrılmış birden fazla anahtar desteklenir. Örn: GROQ_API_KEY = "gsk_1..., gsk_2..."
def parse_keys(secret_value, manual_value):
    if manual_value:
        return [k.strip() for k in manual_value.replace(",", "\n").split("\n") if k.strip()]
    if secret_value:
        if isinstance(secret_value, list):
            return secret_value
        return [k.strip() for k in str(secret_value).replace(",", "\n").split("\n") if k.strip()]
    return []

raw_groq_secret = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
raw_gemini_secret = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""

# --- OTURUM DURUMLARI (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Sarah, your AI English teacher. How are you doing today? Let's practice speaking!"}
    ]

if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"word": "Resilient", "meaning": "Dayanıklı, dirençli", "example": "You must be resilient when learning a new language."},
        {"word": "Multitask", "meaning": "Aynı anda birden fazla iş yapmak", "example": "Our system handles multiple API keys effortlessly."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

# --- SIDEBAR (KONTROL PANELİ VE ÇOKLU ANAHTAR GİRİŞİ) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    
    with st.expander("🔑 Çoklu API Anahtarları (Gizli Ayar)"):
        st.caption("Birden fazla anahtarı virgülle veya alt alta yazabilirsiniz.")
        manual_groq = st.text_area("Groq API Key(ler)", value="", placeholder="gsk_key1, gsk_key2")
        manual_gemini = st.text_area("Gemini API Key(ler)", value="", placeholder="AIza_key1, AIza_key2")

    groq_keys = parse_keys(raw_groq_secret, manual_groq)
    gemini_keys = parse_keys(raw_gemini_secret, manual_gemini)

    st.write(f"**Yüklü Groq Key Sayısı:** {len(groq_keys)}")
    st.write(f"**Yüklü Gemini Key Sayısı:** {len(gemini_keys)}")
    
    st.divider()
    app_mode = st.radio("Mod Seçimi", ["🗣️ Canlı Sesli Sohbet", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Samimi Arkadaş", "Sabırlı Eğitmen", "Enerjik Koç"])

system_prompt = f"You are Sarah, a friendly and warm female English AI teacher ({teacher_persona}) talking with a {selected_level} student. Keep your answers short, natural, conversational, correct mistakes gently, and always end with a quick follow-up question to keep the conversation flowing."


# ==============================================================================
# AKILLI ÇOKLU API DÖNGÜSÜ İLE YANIT ÜRETME FONKSİYONLARI
# ==============================================================================
def get_ai_response(messages_payload):
    # 1. Önce GROQ anahtarlarını sırayla dene
    for g_key in groq_keys:
        try:
            client = Groq(api_key=g_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages_payload,
                temperature=0.7,
                max_tokens=300
            )
            return completion.choices[0].message.content, "Groq"
        except Exception:
            continue # Hata alrsa sonraki Groq anahtarına geç

    # 2. Groq'lar bittiyse veya hata verdiyse GEMINI anahtarlarını sırayla dene
    chat_history_str = "\n".join([f"{m['role']}: {m['content']}" for m in messages_payload if m['role'] != 'system'])
    for gem_key in gemini_keys:
        try:
            g_client = genai.Client(api_key=gem_key)
            res = g_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=f"{system_prompt}\n\nChat History:\n{chat_history_str}"
            )
            return res.text, "Gemini"
        except Exception:
            continue # Hata alrsa sonraki Gemini anahtarına geç

    return None, None


def get_transcription(audio_bytes):
    # Ses dönüşümü için Groq anahtarlarını sırayla dene
    for g_key in groq_keys:
        try:
            client = Groq(api_key=g_key)
            audio_io = io.BytesIO(audio_bytes)
            audio_io.name = "speech.wav"
            transcription = client.audio.transcriptions.create(
                file=(audio_io.name, audio_io.read()),
                model="whisper-large-v3",
                response_format="text",
                language="en"
            )
            return transcription.strip()
        except Exception:
            continue
    return None


# ==============================================================================
# MOD 1: CANLI SESLİ & YAZILI SOHBET
# ==============================================================================
if app_mode == "🗣️ Canlı Sesli Sohbet":
    
    col_avatar, col_info = st.columns([1, 5])
    with col_avatar:
        st.image(
            "https://static.vecteezy.com/system/resources/previews/060/362/634/non_2x/cartoon-female-teacher-avatar-with-glasses-isolated-in-a-bright-friendly-setting-3d-cartoon-female-teacher-educator-avatar-isolated-on-transparent-background-free-png.png", 
            width=100
        )
    with col_info:
        st.markdown("### Sarah (AI English Teacher)")
        st.caption("Çoklu API yük dengeleme sistemi aktif. Sistem, anahtarlarınızda bir yoğunluk veya 503 hatası olduğunda otomatik olarak yedek anahtarlara geçer.")

    st.divider()

    for msg in st.session_state.messages:
        avatar_icon = "👩‍🏫" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    user_query = ""

    st.markdown("---")
    st.markdown("🎙️ **Cevabınızı sesli kaydedin veya yazın:**")
    
    col_mic, col_txt = st.columns([1, 1])
    
    with col_mic:
        audio_file_input = st.audio_input("Konuşmak için tıklayın")
        if audio_file_input is not None and groq_keys:
            with st.spinner("Sarah sesinizi dinliyor..."):
                transcribed = get_transcription(audio_file_input.getvalue())
                if transcribed:
                    user_query = transcribed
                else:
                    st.warning("Ses metne dönüştürülemedi, lütfen tekrar deneyin.")

    with col_txt:
        text_query = st.chat_input("Veya buraya yazıp gönderin...")
        if text_query:
            user_query = text_query

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)

        ai_response = ""
        used_engine = ""

        with st.chat_message("assistant", avatar="👩‍🏫"):
            with st.spinner("Sarah düşünüyor..."):
                messages_payload = [{"role": "system", "content": system_prompt}]
                messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                ai_response, used_engine = get_ai_response(messages_payload)

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
                else:
                    st.error("Tüm API anahtarlarınızda kota dolumu veya sunucu hatası (503) oluştu. Lütfen sol menüden yeni anahtar ekleyin.")


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
