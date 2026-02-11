import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- ESTILO ---
st.set_page_config(page_title="RRB", layout="wide")
st.markdown("""<style>
.stMetric { background: white; padding: 15px; border-radius: 10px; 
border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>""", unsafe_allow_html=True)

# --- DB ---
try:
    u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(u, k)
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.title("🛡️ RRB")
m = st.sidebar.radio("Menu", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# --- 1. FUNCIONÁRIO ---
if m == "👤 Func":
    st.subheader("🔎 Consulta")
    cpf = st.text_input("CPF")
    c = "".join(filter(str.isdigit, cpf))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg = len(hist)
            try: tt = int(float(d.get('parcelas_total', 0)))
            except: tt = 0
            st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Banco", d.get('banco_nome'))
            c3.metric("Status", "OK" if d['diferenca']==0 else "Erro")
            if tt > 0: st.progress(min(1.0, pg/tt))

# --- 2. EMPRESA ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_in = st.text_input("Login")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
    else:
        st.subheader(f"🏢 {st.session_state.n}")
        if st.sidebar.button("SAIR"): st.session_state.at = False; st.rerun()
        with st.expander("📥 Sincronizar"):
            if st.button("EXECUTAR"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = pd.to_numeric(r['valor_rh'], 'coerce')
                        vb = pd.to_numeric(r['valor_banco'], 'coerce')
                        tp = pd.to_numeric(r['total_parcelas'], 'coerce')
                        vr = float(vr) if pd.notna(vr) else 0.0
                        vb = float(vb) if pd.notna(vb) else 0.0
                        tp = int(tp) if pd.notna(tp) else 0
                        #
