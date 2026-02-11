import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

st.markdown("""<style>
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; }
    .logo-container { display: flex; align-items: center; gap: 15px; }
    .logo-text { font-size: 26px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 20px; border-radius: 15px; border: 1px solid #ddd; }
</style>""", unsafe_allow_html=True)

def render_header(t):
    st.markdown(f"<div class='logo-container'><h2>🛡️ RRB | {t}</h2></div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nos Secrets."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Menu", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- 1. FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Funcionário")
    cpf_in = st.text_input("CPF (números)")
    c_cl = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("BUSCAR") and c_cl:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_cl).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d.get('nome_funcionario')}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            st_at = "✅ OK" if d.get('diferenca', 0) == 0 else "⚠️ Erro"
            c3.metric("Status", st_at)
            
            t, p = int(d.get('parcelas_total', 0)), int(d.get('parcelas_pagas', 0))
            with st.expander("Detalhes do Empréstimo", expanded=True):
                st.write(f"**Contrato:** {d.get('contrato_id')}")
                st.write(f"**Pagas:** {p} | **Faltam:** {max(0, t-p)} | **Total:** {t}")
                if t > 0: st.progress(min(1.0, p/t))
        else: st.warning("Não encontrado.")

# --- 2. EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u_in = st.text_input("Usuário")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            # LINHA PROTEGIDA CONTRA CORTE:
            if q.data:
                valid_pass = q.data[0]['senha']
                if h(p_in) == valid_pass:
                    st.session_state.at = True
                    st.session_state.n = q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0]['link_planilha']
                    st.rerun()
                else: st.error("Senha incorreta.")
            else: st.error("Usuário não existe.")
    else:
        st.subheader(f"Empresa: {st.session_state.n}")
        if st.sidebar.button("SAIR"): st.session_state.at = False; st.rerun()
        if st.button("🔄 SINCRONIZAR"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
