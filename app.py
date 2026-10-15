import os
import io
import json
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
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stChatBox {
        border-radius: 12px;
    }
    .css-1v0mbdj {
        border-radius: 16px;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        opacity: 0.9;
        transform: translateY(-2px);
    }
    </style>
""", unsafe_allow_html=True)

# --- GÜVENL
