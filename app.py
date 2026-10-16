import os
import io
import json
import base64
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS
from PIL import Image

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - İngilizce Konuşma & Kelime Pratiği", 
    page_icon="🇬🇧", 
    layout="wide"
)

# --- AVATAR GÖRSELİNİ YÜKLEME ---
# Buradaki dosya yolunu kendi avatar görselinizin yolu ile değiştirin
avatar_image_path = "path/to/your/avatar.png" 
avatar_image = Image.open(avatar_image_path)

# --- ÖZEL CSS (Net Okunabilirlik ve Görünürlük) ---
st.markdown("""
<style>
.user-msg {
    background-color: #1b5e20;
    color: #ffffff !important;
    padding: 14px 18px;
    border-radius: 12px;
    margin: 10px 0;
    text-align: right;
    font-size: 16px;
    font-weight: 600;
}
.assistant-msg {
    background-color: #212121;
    color: #ffffff !important;
    padding: 14px 18px;
    border-radius: 12px;
    margin: 10px 0;
    text-align: left;
    font-size: 16px;
    border-left: 5px solid #4CAF50;
}
div[data-testid="stAudioInput"] {
    background-color: #1E1E1E;
    border: 2px dashed #4CAF50;
    border-radius: 12px;
    padding: 10px;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 15px;
}
div[data-testid="stAudioInput"] button {
    background-color: #4CAF50 !important;
    color: white !important;
    font-size: 16px !important;
    font-weight: bold !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
}
</style>
""", unsafe_allow_html=True)

# --- GÜVENLİ VE ESNEK API ANAHTARI YÖNETİMİ ---
def get_groq_key():
    try:
        if hasattr(st, "secrets"):
            if "api_keys" in st.secrets and "groq_keys" in st.secrets["api_keys"]:
                keys = st.secrets["api_keys"]["groq_keys"]
                if isinstance(keys, list) and len(keys) > 0:
                    return keys[0]
            if "groq_keys" in st.secrets:
                keys = st.secrets["groq_keys"]
                if isinstance(keys, list) and len(keys) > 0:
                    return keys[0]
            if "GROQ_API_KEY" in st.secrets:
                return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "")

def get_gemini_key():
    try:
        if hasattr(st, "secrets"):
            candidates = []
            if "api_keys" in st.secrets and "gemini_keys" in st.secrets["api_keys"]:
                candidates = st.secrets["api_keys"]["gemini_keys"]
            elif "gemini_keys" in st.secrets:
                candidates = st.secrets["gemini_keys"]
            elif "GEMINI_API_KEY" in st.secrets:
                candidates = [st.secrets["GEMINI_API_KEY"]]
            elif "GOOGLE_API_KEY" in st.secrets:
                candidates = [st.secrets["GOOGLE_API_KEY"]]
            
            if isinstance(candidates, list):
                for k in candidates:
                    if k and isinstance(k, str) and k.startswith("AIza"):
                        return k
                if len(candidates) > 0 and isinstance(candidates[0], str):
                    return candidates[0]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

extracted_groq = get_groq_key()
extracted_gemini = get_gemini_key()

# --- OTURUM DURUMLARI (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

if "flashcards" not in st.session_state:
    st.session_state.flashcards = [
        {"word": "Persevere", "meaning": "Azim göstermek, sebat etmek", "example": "You must persevere to master a new language."},
        {"word": "Fluency", "meaning": "Akıcılık", "example": "Daily practice will help you reach fluency."},
        {"word": "Vocabulary", "meaning": "Kelime bilgisi", "example": "Flashcards are great for building vocabulary."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

if "show_meaning" not in st.session_state:
    st.session_state.show_meaning = False

# --- SIDEBAR (AYARLAR VE MOD SEÇİMİ) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    
    use_manual_keys = st.checkbox("Özel API Anahtarı Gir / Düzenle", value=False)
    
    if use_manual_keys or not extracted_groq:
        groq_api_key = st.text_input("Groq API Key", type="password", value=extracted_groq)
    else:
        groq_api_key = extracted_groq
        st.success("🔒 Groq API anahtarı yüklendi.")

    if use_manual_keys or not extracted_gemini:
        gemini_api_key = st.text_input("Gemini API Key (AIzaSy...)", type="password", value=extracted_gemini)
    else:
        gemini_api_key = extracted_gemini
        st.success("🔒 Gemini API anahtarı yüklendi.")
    
    st.divider()
    app_mode = st.radio("Uygulama Modu", ["🗣️ Canlı Sohbet & Sesli Pratik", "🎴 Kelime Kartları (Flashcards)"])
    
    st.divider()
    selected_level = st.selectbox("İngilizce Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Sabırlı Öğretmen", "Aşırı Samimi Arkadaş", "İş Dünyası Koçu"])

# --- CLIENT'LARI BAŞLATMA ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

# Tekrarları Önleyen Sıkılaştırılmış Sistem Talimatı
system_prompt = f"""You are a concise English AI tutor ({teacher_persona}) for a {selected_level} student.
CRITICAL RULES:
1. Provide EXACTLY ONE response to the user's question. Never duplicate or repeat your answers.
​2. Answer directly and stay strictly relevant to the user's message.
3. Always respond in English."""


# ==============================================================================
# MOD 1: CANLI SOHBET & SESLİ PRATİK
# ==============================================================================
if app_mode == "🗣️ Canlı Sohbet & Sesli Pratik":
    st.title("🗣️ LearnAI: Canlı İngilizce Pratik")
    st.caption("Groq Whisper (STT) + Groq Llama 3.3 (Hızlı Sohbet) + gTTS (Otomatik Sesli Yanıt)")

    if not groq_client:
        st.error("🚨 Groq API anahtarı bulunamadı! Lütfen sol menüden anahtarınızı girin.")

    # 1. Mevcut mesaj geçmişini doğrudan HTML kartları ile göster
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg"><b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            # Öğretmen mesajının yanına avatar ekleme
            col1, col2 = st.columns([1, 10])
            with col1:
                st.image(avatar_image, width=50)
            with col2:
                st.markdown(f'<div class="assistant-msg"><b>Teacher:</b> {msg["content"]}</div>', unsafe_allow_html=True)
            if "audio_bytes" in msg and msg["audio_bytes"]:
                b64_audio = base64.b64encode(msg["audio_bytes"]).decode("utf-8")
                audio_html = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64_audio}"></audio>'
                st.markdown(audio_html, unsafe_allow_html=True)

    # 2. Girdi Alma (Mikrofon)
    st.markdown("👇 **Sesli yanıt vermek için mikrofona tıklayın:**")
    audio_input_val = st.audio_input("🎤 Konuşmayı Kaydet", key="voice_recorder")
    
    new_user_text = ""

    if audio_input_val is not None:
        audio_bytes = audio_input_val.getvalue()
        # Aynı ses dosyasını tekrar işleyip birden fazla cevap üretmeyi önle
        if st.session_state.last_processed_audio != audio_bytes:
            st.session_state.last_processed_audio = audio_bytes
            with st.spinner("Sesiniz metne dönüştürülüyor..."):
                try:
                    audio_io = io.BytesIO(audio_bytes)
                    audio_io.name = "audio.wav"
                    transcription = groq_client.audio.transcriptions.create(
                        file=(audio_io.name, audio_io.read()),
                        model="whisper-large-v3",
                        response_format="text",
                        language="en"
                    )
                    new_user_text = transcription.strip()
                except Exception as e:
                    st.error(f"Whisper Hatası: {e}")

    # Alternatif Metin Girişi
    text_input_val = st.chat_input("Veya mesajınızı buraya yazın...")
    if text_input_val:
        new_user_text = text_input_val

    # 3. Yanıt Üretme ve Hafızaya Kaydetme
    if new_user_text:
        # Mesajı bir kez ekle
        st.session_state.messages.append({"role": "user", "content": new_user_text})

        with st.spinner("Yapay zeka yanıt veriyor..."):
            messages_payload = [{"role": "system", "content": system_prompt}]
            messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

            try:
                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages_payload,
                    temperature=0.1
                )
                ai_response = completion.choices[0].message.content
            except Exception as e:
                ai_response = f"Yanıt alınamadı: {e}"

            # gTTS ile ses üret
            audio_bytes_data = None
            try:
                tts = gTTS(text=ai_response, lang='en')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                audio_fp.seek(0)
                audio_bytes_data = audio_fp.read()
            except Exception as tts_err:
                pass

            st.session_state.messages.append({
                "role": "assistant", 
                "content": ai_response,
                "audio_bytes": audio_bytes_data
            })

        st.rerun()


# ==============================================================================
# MOD 2: İNTERAKTİF KELİME KARTLARI (FLASHCARDS)
# ==============================================================================
elif app_mode == "🎴 Kelime Kartları (Flashcards)":
    st.title("🎴 Akıllı Kelime Kartları")
    st.caption("Yapay zeka desteğiyle yeni kelimeler öğrenin ve pratik yapın.")

    col_card, col_actions = st.columns([2, 1])

    with col_card:
        cards = st.session_state.flashcards
        idx = st.session_state.card_index

        if cards:
            current_card = cards[idx]
            
            st.markdown(f"""
            <div style="border:2px solid #4CAF50; border-radius:15px; padding:30px; text-align:center; background-color:#1E1E1E;">
                <h1 style="color:#4CAF50; font-size:48px;">{current_card['word']}</h1>
                <p style="color:#A0A0A0; font-size:18px;"><i>"{current_card['example']}"</i></p>
            </div>
            """, unsafe_allow_html=True)

            st.write("")
            
            if st.button("👁️ Türkçe Anlamını Göster / Gizle"):
                st.session_state.show_meaning = not st.session_state.show_meaning

            if st.session_state.show_meaning:
                st.success(f"**Anlamı:** {current_card['meaning']}")

            btn_prev, btn_next = st.columns(2)
            with btn_prev:
                if st.button("⬅️ Önceki Kart"):
                    st.session_state.card_index = (idx - 1) % len(cards)
                    st.session_state.show_meaning = False
                    st.rerun()
            with btn_next:
                if st.button("Sonraki Kart ➡️"):
                    st.session_state.card_index = (idx + 1) % len(cards)
                    st.session_state.show_meaning = False
                    st.rerun()

    with col_actions:
        st.subheader("✨ AI ile Yeni Kelime Üret")
        st.write("Belirli bir konuda Gemini kullanarak kartlarınıza otomatik kelimeler ekleyin:")
        
        topic = st.text_input("Konu Girin (Örn: Business, Travel, Technology)", "Travel")
        
        if st.button("🚀 AI Kartlar Üret"):
            if gemini_client:
                with st.spinner("Yeni kelime kartları hazırlanıyor..."):
                    try:
                        prompt = f"""
                        Generate 3 English vocabulary cards about the topic '{topic}' suitable for {selected_level} level.
                        Return ONLY a valid JSON array of objects with keys "word", "meaning" (in Turkish), and "example" (in English).
                        Do not include markdown or extra text.
                        """
                        res = gemini_client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=prompt
                        )
                        clean_json = res.text.replace("```json", "").replace("```", "").strip()
                        new_cards = json.loads(clean_json)
                        st.session_state.flashcards.extend(new_cards)
                        st.success(f"'{topic}' konusundan {len(new_cards)} yeni kelime eklendi!")
                    except Exception as e:
                        st.error(f"Kelime üretilirken hata oluştu: {e}")
            else:
                st.error("Lütfen geçerli bir Gemini API Key olduğundan emin olun.")
