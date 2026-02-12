import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.05);
        padding: 15px 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    @media (prefers-color-scheme: dark) { .logo-text { color: #4A90E2; } }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:gray; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

# --- 2. CONEXÃO E AUXILIARES ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("⚠️ Configurações de banco de dados não detectadas.")
        st.stop()
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if st.session_state.get('at'):
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Sair do Painel"):
        logout()

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para consultar sua auditoria.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA", use_container_width=True) and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                if str(dt_nasc_in) == str(d.get("data_nascimento", "")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Olá, {d.get('nome_funcionario')}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Valor RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Banco", d.get('banco_nome', 'N/A'))
                    status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status", status)
                else: st.error("Dados incorretos.")
            else: st.warning("CPF não localizado.")
        except: st.error("Erro de conexão.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st
