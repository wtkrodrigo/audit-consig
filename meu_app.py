import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Gestão Pro", layout="wide", page_icon="🛡️")

# --- DESIGN (CSS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.main { background-color: #f0f2f6; }
.header-container {
    display: flex; align-items: center; justify-content: center;
    padding: 20px; background: white; border-radius: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 25px;
}
.shield-icon {
    background: linear-gradient(135deg, #002D62 0%, #d90429 100%);
    color: white; padding: 15px; border-radius: 12px; margin-right: 15px; font-size: 30px;
}
.logo-text { font-weight: 800; font-size: 32px; color: #002D62; margin: 0; }
.logo-sub { color: #d90429; }
div.stButton > button:first-child {
    background: #002D62; color: white; border-radius: 10px; width: 100%; font-weight: 700;
}
.audit-card {
    background: white; padding: 20px; border-radius: 15px;
    border-left: 5px solid #002D62; margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Erro nos Secrets do Supabase.")
    st.stop()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password)
