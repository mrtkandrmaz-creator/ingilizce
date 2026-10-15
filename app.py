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
        {"word": "Persevere", "meaning": "Azim göstermek, sebat etmek", "example": "You must persevere to master a new language."},
        {"word": "Fluency", "meaning": "Akıcılık", "example": "Daily practice will help you reach fluency."}
    ]

if "card_index" not in st.session_state:
    st.session_state.card_index = 0

if "show_meaning" not in st.session_state:
    st.session_state.show_meaning = False

# --- SIDEBAR (KONTROL PANELİ) ---
with st.sidebar:
    st.title("⚙️ Kontrol Paneli")
    
    manual_groq = st.text_input("Groq API Key (Yedek)", type="password", value="")
    manual_gemini = st.text_input("Gemini API Key (Yedek)", type="password", value="")
    
    if manual_groq:
        groq_api_key = manual_groq
    if manual_gemini:
        gemini_api_key = manual_gemini

    st.divider()
    st.write("**Hibrit Motor Durumu:**")
    st.write(f"Groq API: {'✅ Aktif' if groq_api_key else '❌ Yok'}")
    st.write(f"Gemini API: {'✅ Aktif' if gemini_api_key else '❌ Yok'}")
    
    st.divider()
    app_mode = st.radio("Uygulama Modu", ["🗣️ Canlı Sohbet & Pratik", "🎴 Kelime Kartları"])
    selected_level = st.selectbox("Seviyeniz", ["Beginner (A1-A2)", "Intermediate (B1-B2)", "Advanced (C1-C2)"])

# --- İSTEMCİLERİ BAŞLATMA ---
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

# System Prompt
system_prompt = f"You are a helpful and friendly English AI teacher for a {selected_level} student. Always answer in correct English, correct big mistakes gently, and always end your response with a follow-up question to keep the chat going."


# ==============================================================================
# MOD 1: CANLI SOHBET & HİBRİT / OTOMATİK YEDEKLEME MOTORU
# ==============================================================================
if app_mode == "🗣️ Canlı Sohbet & Pratik":
    st.title("🗣️ LearnAI: Canlı İngilizce Pratik (Akıllı Hibrit Mod)")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("İngilizce mesajınızı yazın...")

    if user_query:
        if not groq_client and not gemini_client:
            st.error("Hiçbir API anahtarı bulunamadı! Lütfen sol menüye en az bir anahtar girin.")
        else:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            ai_response = ""
            success = False

            with st.chat_message("assistant"):
                with st.spinner("Yapay zeka yanıt hazırlıyor..."):
                    
                    # 1. ÖNCE GROQ DENEYELİM (Groq aktifse)
                    if groq_client and not success:
                        try:
                            messages_payload = [{"role": "system", "content": system_prompt}]
                            messages_payload.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                            # En kararlı Groq model adlarından biri
                            completion = groq_client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=messages_payload,
                                temperature=0.7
                            )
                            ai_response = completion.choices[0].message.content
                            success = True
                        except Exception as e:
                            # Groq hata verirse sessizce Gemini'ye geçecek
                            pass

                    # 2. EĞER GROQ BAŞARISIZ OLURSA VEYA YOKSA GEMİNİ DEVREYE GİRER
                    if gemini_client and not success:
                        try:
                            chat_history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                            gemini_full_prompt = f"{system_prompt}\n\nChat History:\n{chat_history_str}\n\nRespond as the teacher:"
                            
                            res = gemini_client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=gemini_full_prompt
                            )
                            ai_response = res.text
                            success = True
                        except Exception as e:
                            st.error(f"Tüm yapay zeka servislerinde hata oluştu: {e}")

                    # Yanıtı ekrana bas ve seslendir
                    if success and ai_response:
                        st.markdown(ai_response)
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})

                        try:
                            tts = gTTS(text=ai_response, lang='en')
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
    st.title("🎴 Akıllı Kelime Kartları")
    cards = st.session_state.flashcards
    idx = st.session_state.card_index

    if cards:
        current_card = cards[idx]
        st.info(f"**Kelime:** {current_card['word']} \n\n *Örnek:* {current_card['example']}")
        
        if st.button("👁️ Anlamını Göster"):
            st.success(f"Anlamı: {current_card['meaning']}")

        if st.button("Sonraki Kart ➡️"):
            st.session_state.card_index = (idx + 1) % len(cards)
            st.rerun()
