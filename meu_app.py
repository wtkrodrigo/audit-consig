import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO (FORÇANDO CORES ESCURAS) ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    /* 1. Fundo da página e containers */
    .stApp { background-color: #f4f7f9 !important; }
    
    /* 2. CARD DA MÉTRICA: Fundo sempre branco e borda visível */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6 !important;
        padding: 15px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }

    /* 3. TÍTULO DA MÉTRICA (Label): Forçar Cinza Escuro */
    [data-testid="stMetricLabel"] p {
        color: #444444 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    /* 4. VALOR DA MÉTRICA: Forçar Azul Escuro RRB */
    [data-testid="stMetricValue"] div {
        color: #002D62 !important;
        font-weight: 800 !important;
    }

    /* Estilos Adicionais */
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    hr { margin-top: 0; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>""", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nos Secrets. Verifique SUPABASE_URL e SUPABASE_KEY."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para acessar o resultado da auditoria.")
        c1, c2, c3 = st.columns([2, 2, 1])
        cpf_in = c1.text_input("CPF (somente números)", placeholder="000.000.000-00")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = c3.text_input("Final Tel (4 dígitos)", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 CONSULTAR AUDITORIA") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
