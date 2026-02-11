import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; }
    .header { display: flex; align-items: center; gap: 12px; background: white; padding: 15px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px #0001; }
    .shield { font-size: 35px; color: #002D62; border-right: 2px solid #eee; padding-right: 15px; }
    .brand { font-weight: 900; font-size: 24px; color: #002D62; }
    .dot { color: #d90429; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="header"><div class="shield">🛡️</div><div class="brand">RRB<span class="dot">.</span>SOLUÇÕES</div></div>', unsafe_allow_html=True)

# --- CONEXÃO BANCO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nas Secrets do Supabase."); st.stop()

def h
