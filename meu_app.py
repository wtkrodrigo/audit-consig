import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- ESTILO PREMIUM ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; width: 100%; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    u, k = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(u, k)
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.title("🛡️ RRB CORPORATE")
m = st.sidebar.radio("Menu", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta de Auditoria")
    cpf = st.text_input("CPF (somente números)")
    c = "".join(filter(str.isdigit, cpf))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg = len(hist)
            # Tratamento seguro para conversão de parcelas
            try: tt = int(float(d.get('parcelas_total', 0)))
            except: tt = 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Erro")
            if tt > 0: st.progress(min(1.0, pg/tt))
        else: st.warning("Dados não localizados.")

# --- 2. MÓDULO EMPRESA ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        with st.columns([1,1.5,1])[1]:
            st.subheader("🔐 Login Empresa")
            u_in = st.text_input("Login")
            p_in = st.text_input("Senha", type='password')
            if st.button("ENTRAR"):
                q = sb.table("empresas").select("*").eq("login", u_in).execute()
                if q.data and h(p_in) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
    else:
        col_t, col_s = st.columns([4, 1])
        col_t.subheader(f"🏢 Gestão: {st.session_state.n}")
        if col_s.button("SAIR"):
            st.session_state.at = False; st.rerun()

        with st.expander("📥 Sincronização Mensal"):
            if st.button("SINCRONIZAR AGORA"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        # Conversão ultra-segura para evitar o erro de 'int'
                        vr = pd.to_numeric(r['valor_rh'], 'coerce')
                        vb = pd.to_numeric(r['valor_banco'], 'coerce')
                        tp = pd.to_numeric(r['total_parcelas'], 'coerce')
                        vr = float(vr) if pd.notna(vr) else 0.0
                        vb = float(vb) if pd.notna(vb) else 0.0
                        tp = int(tp) if pd.notna(tp) else 0
                        
                        pld = {
                            "nome_empresa": st.session_state.n, "cpf": str(r['cpf']),
                            "nome_funcionario": str(r['nome']), "valor_rh": vr,
                            "valor_banco": vb, "diferenca": vr - vb,
                            "banco_nome": str(r.get('banco', 'N/A')),
                            "contrato_id": str(r.get('contrato', 'N/A')),
                            "parcelas_total": tp, "data_processamento": datetime
