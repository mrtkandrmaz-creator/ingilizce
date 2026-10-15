import os
import io
import json
import streamlit as st
from groq import Groq
from google import genai
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - İngilizce Konuşma & Kelime Pratiği", 
    page_icon="🇬🇧", 
    layout="wide"
)

# --- CSS İLE METİN VE CHAT GÖRÜNÜRLÜK AYARLARI ---
st.markdown("""
<style>
/* Sohbet mesajlarındaki yazıların her temada net okunması için stil ayarı */
div[data-testid="stChatMessage"] {
    background-color: #262730;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 10px;
}
div[data-testid="stChatMessage"] p {
    color: #FFFFFF !important;
    font-size: 16px !important;
}
/* Modern Mikrofon Kutusu Tasarımı */
div[data-testid="stAudioInput"] {
    background-color: #1E1E1E;
    border: 2px dashed #4CAF50;
    border-radius: 12px;
    padding: 10px;
    text-align: center;
    margin-top: 5px;
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

# Sıkılaştırılmış Sistem Promptu
system_prompt = f"""You are a helpful and friendly English AI teacher ({teacher_persona}) for a {selected_level} student. 
CRITICAL RULE: Always stay strictly focused on the user's input, answer their specific question directly, and do not wander off to unrelated topics. 
Always answer in English, correct big mistakes gently, and keep the conversation relevant to what the user just said."""


# ==============================================================================
# MOD 1: CANLI SOHBET & SESLİ PRATİK
# ==============================================================================
if app_mode == "🗣️ Canlı Sohbet & Sesli Pratik":
    st.title("🗣️ LearnAI: Canlı İngilizce Pratik")
    st.caption("Groq Whisper (STT) + Groq Llama 3.3 (Hızlı Sohbet) + gTTS (Otomatik Sesli Yanıt)")

    if not groq_client:
        st.error("🚨 Groq API anahtarı bulunamadı! Lütfen sol menüden anahtarınızı girin.")

    user_text = ""

    # 1. Başlangıçta henüz mesaj yoksa en üste karşılama mikrofonu koyalım
    if not st.session_state.messages:
        st.info("👋 İngilizce pratik yapmak için aşağıdaki mikrofona tıklayarak konuşmaya başlayın!")
        audio_file_input = st.audio_input("🎤 Konuşmaya Başla")
        if audio_file_input is not None and groq_client:
            with st.spinner("Sesiniz metne dönüştürülüyor..."):
                try:
                    audio_bytes = audio_file_input.getvalue()
                    audio_io = io.BytesIO(audio_bytes)
                    audio_io.name = "audio.wav"
                    transcription = groq_client.audio.transcriptions.create(
                        file=(audio_io.name, audio_io.read()),
                        model="whisper-large-v3",
                        response_format="text",
                        language="en"
                    )
                    user_text = transcription.strip()
                except Exception as e:
                    st.error(f"Hata: {e}")
    
    # 2. Mevcut mesaj geçmişini ekrana yazdır (Kullanıcı ve Asistan mesajları)
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and "audio_bytes" in msg:
                st.audio(msg["audio_bytes"], format="audio/mp3", autoplay=True)
        
        # Asistan mesajının hemen altına yeni sesli yanıt mikrofonunu yerleştir
        if msg["role"] == "assistant" and i == len(st.session_state.messages) - 1:
            st.markdown("👇 **Sesli yanıt vermek için mikrofona tıklayın:**")
            audio_file_input = st.audio_input(f"🎤 Sesli Yanıt Ver (Cevap #{i})")
            
            if audio_file_input is not None and groq_client:
                with st.spinner("Sesiniz metne dönüştürülüyor..."):
                    try:
                        audio_bytes = audio_file_input.getvalue()
                        audio_io = io.BytesIO(audio_bytes)
                        audio_io.name = "audio.wav"
                        transcription = groq_client.audio.transcriptions.create(
                            file=(audio_io.name, audio_io.read()),
                            model="whisper-large-v3",
                            response_format="text",
                            language="en"
                        )
                        user_text = transcription.strip()
                    except Exception as e:
                        st.error(f"Hata: {e}")

    # Alternatif Metin Girişi
    st.markdown("---")
    text_input_val = st.chat_input("Veya İngilizce mesajınızı buraya yazın...")
    if text_input_val:
        user_text = text_input_val

    # 3. Kullanıcıdan bir girdi (Ses veya Yazı) geldiyse HEMEN ekrana yaz ve işleme koy
    if user_text:
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.write(user_text)

        if groq_client:
            with st.chat_message("assistant"):
                with st.spinner("Yapay zeka yanıt veriyor..."):
                    messages_payload = [{"role": "system", "content": system_prompt}]
                    messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                    try:
                        completion = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=messages_payload,
                            temperature=0.5
                        )
                        ai_response = completion.choices[0].message.content
                    except Exception as e:
                        try:
                            completion = groq_client.chat.completions.create(
                                model="openai/gpt-oss-20b",
                                messages=messages_payload,
                                temperature=0.5
                            )
                            ai_response = completion.choices[0].message.content
                        except Exception as e2:
                            ai_response = f"Groq API Hatası: {e2}"

                    st.write(ai_response)

                    # gTTS ile otomatik seslendirme
                    try:
                        tts = gTTS(text=ai_response, lang='en')
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        audio_fp.seek(0)
                        audio_bytes_data = audio_fp.read()
                        
                        st.audio(audio_bytes_data, format="audio/mp3", autoplay=True)
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": ai_response,
                            "audio_bytes": audio_bytes_data
                        })
                    except Exception as tts_err:
                        st.warning(f"Ses sentezleme uyarısı: {tts_err}")
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
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
