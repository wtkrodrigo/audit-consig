import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RRB Auditoria - Master", layout="wide")

# Estilos CSS Avançados para Visual Sofisticado
st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-text { font-size: 32px; font-weight: bold; color: #002D62; letter-spacing: -1px; }
    .admin-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; }
    .section-header { color: #002D62; font-size: 20px; font-weight: 600; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

def logo():
    st.markdown("<div class='logo-text'>🛡️ RRB SOLUÇÕES <span style='color:#666; font-weight:normal; font-size:18px;'>| Master Admin</span></div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO SUPABASE ---
try:
    su = st.secrets["SUPABASE_URL"]
    sk = st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except Exception as e:
    st.error("Erro crítico de conexão. Verifique os Secrets.")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.markdown("### 🏢 SISTEMA RRB")
menu = st.sidebar.radio("Navegação Principal", ["👤 Portal do Funcionário", "🏢 Painel da Empresa", "⚙️ Configurações Master"])

# --- MÓDULO 1: FUNCIONÁRIO ---
if menu == "👤 Portal do Funcionário":
    logo()
    st.subheader("Consulta de Auditoria")
    cpf_raw = st.text_input("Digite seu CPF para consultar")
    cpf_clean = "".join(filter(str.isdigit, cpf_raw))
    
    if st.button("CONSULTAR AGORA") and cpf_clean:
        res = sb.table("resultados_auditoria").select("*").eq("cpf", cpf_clean).execute()
        if res.data:
            dados = res.data[-1]
            st.success(f"Registro localizado: {dados['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {dados.get('valor_rh', 0):,.2f}")
            c2.metric("Banco de Origem", dados.get('banco_nome', 'N/A'))
            c3.metric("Status", "✅ CONFORMIDADE" if dados.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA")
        else:
            st.warning("Dados não encontrados para este CPF.")

# --- MÓDULO 2: EMPRESA ---
elif menu == "🏢 Painel da Empresa":
    logo()
    if 'autenticado' not in st.session_state: st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        with st.container():
            st.info("Acesse com suas credenciais de parceiro RRB.")
            u_in = st.text_
