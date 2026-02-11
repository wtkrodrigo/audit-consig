import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="RRB", layout="wide", page_icon="🛡️")
st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; box-shadow: 0 2px 5px #0001; }
    .header { display: flex; align-items: center; gap: 12px; background: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 5px #0001; }
    .shield { font-size: 30px; border-right: 2px solid #eee; padding-right: 15px; }
    .brand { font-weight: 900; font-size: 22px; color: #002D62; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="header"><div class="shield">🛡️</div><div class="brand">RRB<span style="color:#d90429">.</span>SOLUÇÕES</div></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. MÓDULO FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("Consulta
