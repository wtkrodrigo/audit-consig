import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB", layout="wide")

# --- CONEXAO ---
try:
    su = st.secrets["SUPABASE_URL"]
    sk = st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro Secrets"); st.stop()

def h(p):
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
m = st.sidebar.selectbox("Menu", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONARIO
if m == "👤 Func":
    st.subheader("🔎 Status")
    c_in = st.text_input("CPF")
    c = "".join(filter(str.isdigit, c_in))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pagas = len(hist)
            total = int(d.get('parcelas_total', 0))
            st.info(f"🏦 {d.get('banco_nome')} | 📄 CTR: {ct}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Pagas", f"{pagas}/{total}")
            c2.metric("Restam", f"{max(0, total - pagas)}")
            c3.metric("Status", "OK" if d['diferenca']==0 else "Erro")
            if total > 0: st.progress(min(1.0, pagas/total))
        else: st.warning("Não encontrado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_in = st.text_input("Login")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
    else:
        col_t, col_s = st.columns([4, 1])
        col_t.subheader(f"Gestão: {st.session_state.n}")
        if col_s.button("SAIR"):
            st.session_state.at = False; st.rerun()
            
        if st.button("🔄 ATUALIZAR"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                df = df.dropna(subset=['cpf', 'nome'])
                for _, r in df.iterrows():
                    vr = pd.to_numeric(r['valor_rh'], errors='coerce')
                    vb = pd.to_numeric(r['valor_banco'], errors='coerce')
                    tp = pd.to_numeric(r['total_parcelas'], errors='coerce')
                    vr = 0.0 if pd.isna(vr) else float(vr)
                    vb = 0.0 if pd.isna(vb) else float(vb)
                    tp = 0 if pd.isna(tp) else int(tp)
                    pld = {
                        "nome_empresa": st.session_state.n,
                        "cpf": str(r['cpf']), "nome_funcionario": str(r['nome']),
                        "valor_rh": vr, "valor_banco": vb, "diferenca": vr - vb,
                        "banco_nome": str(r.get('banco', 'N/A')),
                        "contrato_id": str(r.get('contrato', 'N/A')),
                        "parcelas_total": tp,
                        "data_processamento": datetime.now().isoformat()
                    }
                    sb.table("resultados_auditoria").insert(pld).execute()
                st.success("Sincronizado!")
            except Exception as e: st.error(f"Erro: {e}")

        st.write("---")
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).order(
            "data_processamento", desc=True).limit(20).execute()
        if res
