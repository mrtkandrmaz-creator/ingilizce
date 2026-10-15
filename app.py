import os
import io
import json
import streamlit as st
from groq import Groq
from google import genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="LearnAI - İngilizce Konuşma & Kelime Pratiği", 
    page_icon="🇬🇧", 
    layout="wide"
)

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
    groq_api_key = st.text_input("Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
    gemini_api_key = st.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
    
    st.divider()
    app_mode = st.radio("Uygulama Modu", ["🗣️ Canlı Sohbet & Sesli Pratik", "🎴 Kelime Kartları (Flashcards)"])
    
    st.divider()
    selected_level = st.selectbox("İngilizce Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])
    teacher_persona = st.selectbox("Öğretmen Tarzı", ["Sabırlı Öğretmen", "Aşırı Samimi Arkadaş", "İş Dünyası Koçu"])

# --- CLIENT'LARI BAŞLATMA ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

# System Prompt Hazırlığı
system_prompt = f"""You are a helpful and friendly English AI teacher ({teacher_persona}) for a {selected_level} student. 
Keep your conversation flow natural. 
Always answer in English, correct big mistakes gently, and end your response with a follow-up question to keep the chat going."""


# ==============================================================================
# MOD 1: CANLI SOHBET & SESLİ PRATİK
# ==============================================================================
if app_mode == "🗣️ Canlı Sohbet & Sesli Pratik":
    st.title("🗣️ LearnAI: Canlı İngilizce Pratik")
    st.caption("Groq Whisper (STT) + Groq Llama 3 (Hızlı Sohbet) + Gemini (Gramer Analizi) + gTTS (TTS)")

    # İki Kolonlu Düzen: Sol tarafta Sohbet, Sağ tarafta Gemini Gramer Koçu
    col_chat, col_feedback = st.columns([2, 1])

    with col_chat:
        st.subheader("💬 Sohbet Ekranı")
        
        # Geçmiş Mesajları Göster
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Girdi Alanı (Ses & Metin)
        st.markdown("---")
        st.write("🎙️ **Mikrofon ile Konuşun:**")
        audio_recorded = mic_recorder(
            start_prompt="🔴 Kaydı Başlat", 
            stop_prompt="⏹️ Bitir ve Gönder", 
            key="mic_recorder"
        )
        
        text_input = st.chat_input("Veya buraya İngilizce yazın...")

        user_text = ""

        # 1. MİKROFON GİRDİSİ -> GROQ WHISPER STT
        if audio_recorded and groq_client:
            with st.spinner("Sesiniz Groq Whisper ile metne dönüştürülüyor..."):
                try:
                    audio_bytes = audio_recorded['bytes']
                    audio_file = io.BytesIO(audio_bytes)
                    audio_file.name = "speech.wav"

                    transcription = groq_client.audio.transcriptions.create(
                        file=(audio_file.name, audio_file.read()),
                        model="whisper-large-v3",
                        response_format="text",
                        language="en"
                    )
                    user_text = transcription
                except Exception as e:
                    st.error(f"Groq Whisper Hatası: {e}")

        elif text_input:
            user_text = text_input

        # 2. MESAJ İŞLEME VE SOHBET AKIŞI
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            with st.chat_message("user"):
                st.write(user_text)

            # Groq Llama3 ile Hızlı Yanıt Üretme
            if groq_client:
                with st.chat_message("assistant"):
                    with st.spinner("Yanıt üretiliyor..."):
                        messages_payload = [{"role": "system", "content": system_prompt}]
                        messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                        completion = groq_client.chat.completions.create(
                            model="llama3-70b-8192",
                            messages=messages_payload,
                            temperature=0.7
                        )
                        ai_response = completion.choices[0].message.content
                        st.write(ai_response)
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})

                        # gTTS ile Seslendirme
                        tts = gTTS(text=ai_response, lang='en')
                        audio_fp = io.BytesIO()
                        tts.write_to_fp(audio_fp)
                        audio_fp.seek(0)
                        st.audio(audio_fp, format="audio/mp3", autoplay=True)

    # Sağ Kolon: Gemini ile Gramer ve Kelime Analizi
    with col_feedback:
        st.subheader("🧐 Gemini Gramer Koçu")
        st.caption("Son cümlenizdeki dil bilgisi hataları ve öneriler:")

        if st.session_state.messages and gemini_client:
            last_user_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), None)
            
            if last_user_msg:
                with st.spinner("Gemini cümlenizi inceliyor..."):
                    try:
                        analysis_prompt = f"""
                        Analyze the following English sentence spoken by a student ({selected_level} level):
                        Sentence: "{last_user_msg}"

                        Provide feedback in Turkish:
                        1. **Grammar Correction:** Any mistakes? If yes, show correct version.
                        2. **Better Alternatives:** A more natural native-like phrasing.
                        3. **New Vocabulary:** Highlight 1 useful vocabulary word from the context.
                        Keep it short and encouraging.
                        """
                        response = gemini_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=analysis_prompt,
                        )
                        st.info(response.text)
                    except Exception as e:
                        st.warning(f"Gemini analizi alınamadı: {e}")
        else:
            st.write("Analiz almak için konuşmaya veya yazmaya başlayın!")


# ==============================================================================
# MOD 2: INTERAKTİF KELİME KARTLARI (FLASHCARDS)
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
            
            # Kart Tasarımı
            st.markdown(f"""
            <div style="border:2px solid #4CAF50; border-radius:15px; padding:30px; text-align:center; background-color:#1E1E1E;">
                <h1 style="color:#4CAF50; font-size:48px;">{current_card['word']}</h1>
                <p style="color:#A0A0A0; font-size:18px;"><i>"{current_card['example']}"</i></p>
            </div>
            """, unsafe_allow_html=True)

            st.write("")
            
            # Anlamı Göster / Gizle Butonu
            if st.button("👁️ Türkçe Anlamını Göster / Gizle"):
                st.session_state.show_meaning = not st.session_state.show_meaning

            if st.session_state.show_meaning:
                st.success(f"**Anlamı:** {current_card['meaning']}")

            # İlerleme Butonları
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
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        clean_json = res.text.replace("```json", "").replace("```", "").strip()
                        new_cards = json.loads(clean_json)
                        st.session_state.flashcards.extend(new_cards)
                        st.success(f"'{topic}' konusundan {len(new_cards)} yeni kelime eklendi!")
                    except Exception as e:
                        st.error(f"Kelime üretilirken hata oluştu: {e}")
            else:
                st.error("Lütfen Gemini API Key girin.")