import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; box-shadow: 0 2px 5px #0001; }
    .header { display: flex; align-items: center; gap: 12px; background: white; padding: 15px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px #0000000d; }
    .shield { font-size: 35px; color: #002D62; border-right: 2px solid #eee; padding-right: 15px; }
    .brand { font-weight: 900; font-size: 24px; color: #002D62; }
    .dot { color: #d90429; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="header"><div class="shield">🛡️</div><div class="brand">RRB<span class="dot">.</span>SOLUÇÕES</div></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta de Laudo")
    cpf_in = st.text_input("CPF (somente números)")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR") and cpf:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
        if r.data:
            d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("Folha RH", f"R$ {d['valor_rh']:.2f}")
            c2.metric("Banco", f"R$ {d['valor_banco']:.2f}")
            if d['diferenca'] == 0: st.info("✅ Tudo em dia")
            else: st.error(f"❌ Diferença: R$ {abs(d['diferenca']):.2f}")
        else: st.warning("Não encontrado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.button("🔄 SINCRONIZAR PLANILHA"):
            if st.session_state.lk:
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df['dif'] = df['valor_rh'] - df['valor_banco']
