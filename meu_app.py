import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    su = st.secrets["SUPABASE_URL"]
    sk = st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nas Credenciais"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.markdown("### 🛡️ RRB CORPORATE")
m = st.sidebar.radio("Navegação", 
    ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    st.subheader("🔎 Portal de Transparência")
    cpf_in = st.text_input("CPF para consulta")
    c = "".join(filter(str.isdigit, cpf_in))
    if st.button("CONSULTAR"):
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Bem-vindo, {d['nome_funcionario']}")
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg, tt = len(hist), int(d.get('parcelas_total', 0))
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Banco", d.get('banco_nome'))
            c3.metric("Contrato", ct)
            if tt > 0: st.progress(min(1.0, pg/tt))
        else: st.warning("Dados não localizados.")

# --- 2. MÓDULO EMPRESA ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        with st.columns([1,1.5,1])[1]:
            st.subheader("🔐 Login")
            u_in = st.text_input("Usuário")
            p_in = st.text_input("Senha", type='password')
            if st.button("ENTRAR"):
                q = sb.table("empresas").select("*").eq("login",u_in).execute()
                if q.data and h(p_in) == q.data[0]['senha']:
                    st.session_state.at = True
                    st.session_state.n = q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Erro de login")
    else:
        h1, h2 = st.columns([4, 1])
        h1.subheader(f"🏢 {st.session_state.n}")
        if h2.button("SAIR"):
            st.session_state.at = False; st.rerun()

        # LINHA 72 CORRIGIDA (QUEBRA MANUAL)
        with st.expander("📥 Processar Folha", 
                       expanded=False):
            if st.button("🚀 SINCRONIZAR AGORA"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = pd.to_numeric(r['valor_rh'], errors='coerce')
                        vb = pd.to_numeric(r['valor_banco'], errors='coerce')
                        tp = pd.to_numeric(r['total_parcelas'], errors='coerce')
                        vr, vb = (float(x) if pd.notna(x) else 0.0 for x in [vr, vb])
                        tp = int(tp
