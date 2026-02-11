import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; box-shadow: 0 2px 5px #0001; }
    .header { display: flex; align-items: center; gap: 10px; background: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; }
    .shield { font-size: 35px; color: #002D62; border-right: 2px solid #eee; padding-right: 15px; }
    .brand { font-weight: 900; font-size: 24px; color: #002D62; }
    .dot { color: #d90429; }
</style>""", unsafe_allow_html=True)

# Logotipo Moderno: Escudo + Texto
st.markdown(f'<div class="header"><div class="shield">🛡️</div><div class="brand">RRB<span class="dot">.</span>SOLUÇÕES</div></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()
def ch(p, ht): return h(p) == ht

# --- MENU ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("Consulta Segura")
    cpf_in = st.text_input("Seu CPF")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR") and cpf:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
        if r.data:
            d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("Folha RH", f"R$ {d['valor_rh']}")
            c2.metric("Base Banco", f"R$ {d['valor_banco']}")
            if d['diferenca'] == 0: st.info("✅ Conformidade Detectada")
            else: st.error(f"❌ Divergência: R$ {abs(d['diferenca'])}")
        else: st.warning("Não localizado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and ch(p, q.data[0]['senha']):
                exp = datetime.strptime(q.data[0]['data_expiracao'], "%Y-%m-%d")
                if datetime.now() > exp: st.error("Expirado")
                else: st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']; st.rerun()
    else:
        st.subheader(f"Auditoria: {st.session_state.n}")
        f1, f2 = st.file_uploader("RH"), st.file_uploader("Banco")
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf')
            res['dif'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            k1, k2 = st.columns(2)
            k1.metric("Total", len(res)); k2
