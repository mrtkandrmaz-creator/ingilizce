import os
import io
import json
import streamlit as st
from groq import Groq
import google.generativeai as genai
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - Hızlı İngilizce Asistanı", 
    page_icon="⚡", 
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

# --- ÇOKLU API ANAHTARLARINI OKUMA ---
groq_keys = []
gemini_keys = []

def extract_keys(val):
    if not val:
        return []
    if isinstance(val, list):
        return [str(k).strip() for k in val if str(k).strip()]
    if isinstance(val, str):
        return [k.strip() for k in val.replace(",", "\n").split("\n") if k.strip()]
    return []

try:
    if "api_keys" in st.secrets:
        sec = st.secrets["api_keys"]
        groq_keys = extract_keys(sec.get("groq_keys", []))
        gemini_keys = extract_keys(sec.get("gemini_keys", []))

    if not groq_keys and "GROQ_API_KEY" in st.secrets:
        groq_keys = extract_keys(st.secrets["GROQ_API_KEY"])
        
    if not gemini_keys and "GEMINI_API_KEY" in st.secrets:
        gemini_keys = extract_keys(st.secrets["GEMINI_API_KEY"])
except Exception:
    pass

# --- OTURUM DURUMLARI (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Sarah, your AI English teacher. How can I help you practice today?"}
    ]

if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"word": "Lightning", "meaning": "Yıldırım, çok hızlı", "example": "This app runs at lightning speed."},
        {"word": "Efficient", "meaning": "Verimli, hızlı çalışan", "example": "We use optimized API calls."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

# --- SIDEBAR (KONTROL PANELİ) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    st.write(f"**Groq Key:** {len(groq_keys)} adet")
    st.write(f"**Gemini Key:** {len(gemini_keys)} adet")
    
    st.divider()
    app_mode = st.radio("Mod Seçimi", ["🗣️ Canlı Sohbet", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Samimi Arkadaş", "Sabırlı Eğitmen", "Enerjik Koç"])

system_prompt = f"You are Sarah, a friendly and warm female English AI teacher ({teacher_persona}) talking with a {selected_level} student. Keep your answers short, natural, conversational, correct mistakes gently, and always end with a quick follow-up question."


# ==============================================================================
# HIZLI VE OPTİMİZE YANIT ÜRETME FONKSİYONLARI
# ==============================================================================
def get_ai_response(messages_payload):
    # 1. En hızlı model olan Groq llama-3.1-8b-instant ile hızlıca dene
    for g_key in groq_keys:
        try:
            client = Groq(api_key=g_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # En hızlı ve hafif model
                messages=messages_payload,
                temperature=0.7,
                max_tokens=250
            )
            if completion and completion.choices:
                return completion.choices[0].message.content
        except Exception:
            continue

    # 2. Groq yanıt vermezse Gemini 1.5 Flash ile devam et
    chat_history_str = "\n".join([f"{m['role']}: {m['content']}" for m in messages_payload if m['role'] != 'system'])
    for gem_key in gemini_keys:
        try:
            genai.configure(api_key=gem_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"{system_prompt}\n\nChat History:\n{chat_history_str}")
            if response and hasattr(response, 'text') and response.text:
                return response.text
        except Exception:
            continue

    return "⚠️ Şu an tüm API anahtarlarında yoğunluk yaşanıyor. Lütfen birkaç saniye sonra tekrar deneyin."


def get_transcription(audio_bytes):
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
# MOD 1: CANLI SOHBET
# ==============================================================================
if app_mode == "🗣️ Canlı Sohbet":
    
    col_avatar, col_info = st.columns([1, 5])
    with col_avatar:
        st.image(
            "https://static.vecteezy.com/system/resources/previews/060/362/634/non_2x/cartoon-female-teacher-avatar-with-glasses-isolated-in-a-bright-friendly-setting-3d-cartoon-female-teacher-educator-avatar-isolated-on-transparent-background-free-png.png", 
            width=100
        )
    with col_info:
        st.markdown("### Sarah (AI English Teacher)")
        st.caption("⚡ Ultra hızlı yanıt modu aktif.")

    st.divider()

    for msg in st.session_state.messages:
        avatar_icon = "👩‍🏫" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            st.markdown(msg["content"])

    user_query = ""

    st.markdown("---")
    
    col_mic, col_txt = st.columns([1, 1])
    with col_mic:
        try:
            audio_file_input = st.audio_input("Sesli Mesaj Gönder")
            if audio_file_input is not None and groq_keys:
                with st.spinner("Dinleniyor..."):
                    transcribed = get_transcription(audio_file_input.getvalue())
                    if transcribed:
                        user_query = transcribed
        except Exception:
            pass

    with col_txt:
        text_query = st.chat_input("Mesajınızı yazın...")
        if text_query:
            user_query = text_query

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)

        with st.chat_message("assistant", avatar="👩‍🏫"):
            with st.spinner("Sarah yazıyor..."):
                messages_payload = [{"role": "system", "content": system_prompt}]
                messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                ai_response = get_ai_response(messages_payload)

                if ai_response:
                    st.markdown(ai_response)
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

                    # Seslendirmeyi hatasız ve hızlı yap
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
    st.title("🎴 Kelime Kartları")
    cards = st.session_state.flashcards
    idx = st.session_state.card_index

    if cards:
        current_card = cards[idx]
        st.info(f"**Kelime:** {current_card['word']} \n\n *Örnek:* {current_card['example']}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👁️ Anlamı"):
                st.success(f"Anlamı: {current_card['meaning']}")
        with col2:
            if st.button("➡️ Sonraki"):
                st.session_state.card_index = (idx + 1) % len(cards)
                st.rerun()
