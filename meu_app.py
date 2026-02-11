import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; width: 100%; }
    .logo-text { font-size: 24px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

def mostrar_logo():
    st.markdown("<div class='logo-text'>🛡️ RRB SOLUÇÕES</div>", unsafe_allow_html=True)
    st.caption("Auditoria Inteligente e Transparência")
    st.write("---")

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nas Credenciais"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.title("MENU RRB")
m = st.sidebar.radio("Ir para:", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    mostrar_logo()
    st.subheader("🔎 Minha Auditoria")
    cpf = st.text_input("Digite seu CPF")
    c = "".join(filter(str.isdigit, cpf))
    if st.button("CONSULTAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg = len(hist)
            v_tp = d.get('parcelas_total')
            tt = int(float(v_tp)) if v_tp and str(v_tp).lower() != 'nan' else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Valor Mensal", f"R$ {d.get('valor_rh', 0):.2f}")
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Alerta")
            st.info(f"🏦 Banco: {d.get('banco_nome')} | 📄 Contrato: {ct}")
            if tt > 0: st.progress(min(1.0, pg/tt))
        else: st.warning("CPF não localizado.")

# --- 2. MÓDULO EMPRESA ---
elif m == "🏢 Empresa":
    mostrar_logo()
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        with st.columns([1,1.5,1])[1]:
            st.subheader("🔐 Painel Empresa")
            u_in, p_in = st.text_input("Login"), st.text_input("Senha", type='password')
            if st.button("ACESSAR"):
                q = sb.table("empresas").select("*").eq("login", u_in).execute()
                if q.data and h(p_in) == q.data[0]['senha']:
