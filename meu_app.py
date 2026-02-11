import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB", layout="wide")

st.markdown("""<style>
    .stMetric { background: white; padding: 15px; 
    border-radius: 10px; border-left: 5px solid #002D62; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    s_url = st.secrets["SUPABASE_URL"]
    s_key = st.secrets["SUPABASE_KEY"]
    sb = create_client(s_url, s_key)
except:
    st.error("Erro Secrets"); st.stop()

def h(p):
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
m = st.sidebar.selectbox("Módulo", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONÁRIO
if m == "👤 Func":
    st.subheader("🔎 Status do Empréstimo")
    c_in = st.text_input("CPF (apenas números)")
    c = "".join(filter(str.isdigit, c_in))
    if st.button("VERIFICAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pagas = len(hist)
            total = int(d.get('parcelas_total', 0))
            st.info(f"🏦 {d.get('banco_nome')} | 📄 Contrato: {ct}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Pagas", f"{pagas} de {total}")
            c2.metric("Restantes", f"{max(0, total - pagas)}")
            c3.metric("Status", "OK" if d['diferenca']==0 else "Erro")
            if total > 0:
                st.progress(min(1.0, pagas/total))
        else:
            st.warning("Não encontrado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: 
        st.session_state.at = False
    if not st.session_state.at:
        u_in = st.text_input("Login")
        p_in = st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
    else:
        c_t, c_s = st.columns([4, 1])
        c_t.subheader(f"Gestão: {st.session_state.n}")
        if c_s.button("🔴 SAIR"):
            st.session_state.at = False; st.rerun()
            
        if st.button("🔄 ATUALIZAR E MOSTRAR LISTA"):
            try:
                df_raw = pd.read_csv(st.session_state.lk)
                df_raw.columns = df_raw.columns.str.strip().str.lower()
                df_raw = df_raw.dropna(subset=['cpf', 'nome'])
                for _, r in df_raw.iterrows():
                    v_rh = pd.to_numeric(r['valor_rh'], errors='coerce')
                    v_ba = pd.to_numeric(r['valor_banco'], errors='coerce')
                    t_pa = pd.to_numeric(r['total_parcelas'], errors='coerce')
                    v_rh = 0.0 if pd.isna(v_rh) else float(v_rh)
                    v_ba = 0.0 if pd.isna(v_ba) else float(v_ba)
                    t_pa = 0 if pd.isna(t_pa) else int(t_pa)
                    pld = {
                        "nome_empresa": st.session_state.n,
                        "cpf": str(r['cpf']),
                        "nome_funcionario": str(r['nome']),
                        "valor_rh": v_rh, "valor_banco": v_ba,
                        "diferenca": v_rh - v_ba,
                        "banco_nome": str(r.get('banco', 'N/A')),
                        "contrato_id": str(r.get('contrato', 'N/A')),
                        "parcelas_total": t_pa,
                        "data_processamento": datetime.now().isoformat()
                    }
                    sb.table("resultados_auditoria").insert(pld).execute()
                st.success("✅ Sincronizado!")
            except Exception as e:
