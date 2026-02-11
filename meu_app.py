import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 26px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 25px; border-radius: 12px; border: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    h_html = f"<div class='logo-container'><span style='font-size: 35px;'>🛡️</span>"
    h_html += f"<div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:16px;'>| {titulo}</span></div></div>"
    st.markdown(h_html, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    s_u = st.secrets["SUPABASE_URL"]
    s_k = st.secrets["SUPABASE_KEY"]
    sb = create_client(s_u, s_k)
except Exception:
    st.error("Erro nos Secrets do Supabase.")
    st.stop()

def h(p):
    return hashlib.sha256(str.encode(p)).hexdigest()

T_AUDIT = "resultados_auditoria"
T_EMPRE = "empresas"

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("Valide seus dados abaixo para acessar.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc = c2.date_input("Data de Nascimento", min_value=datetime(1940, 1, 1), format="DD/MM/YYYY")
        tel_fim = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
        
    if st.button("CONSULTAR") and c_clean:
        r = sb.table(T_AUDIT).select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            v_dt = str(dt_nasc) == str(d.get("data_nascimento", ""))
            v_tl = str(d.get("telefone", "")).endswith(tel_fim)
            if v_dt and v_tl:
                st.success(f"Bem-vindo, {d['nome_funcionario']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                m2.metric("Banco", d.get('banco_nome', 'N/A'))
                status = "✅ CONFORME" if d.get
