import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- ESTILO E LOGO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .logo { font-size: 26px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

def logo():
    st.markdown("<div class='logo'>🛡️ RRB SOLUÇÕES</div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nos Secrets (URL/KEY do Supabase)"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.title("PAINEL RRB")
m = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    logo()
    cpf_input = st.text_input("Digite seu CPF")
    c = "".join(filter(str.isdigit, cpf_input))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            # Pega o último registro processado
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            
            c1, c2, c3 = st.columns(3)
            pg = d.get('parcelas_pagas', 1) # Fallback simples
            tt = int(d['parcelas_total']) if d['parcelas_total'] else 0
            
            c1.metric("Parcelas", f"{pg}/{
