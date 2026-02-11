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
            p_pagas = len(hist)
            p_total = int(d.get('parcelas_total', 0))
            st.info(f"🏦 {d.get('banco_nome')} | 📄 CTR: {ct}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Pagas", f"{p_pagas}/{p_total}")
            c2.metric("Restam", f"{max(0, p_total - p_pagas)}")
            c3.metric("Status", "OK" if d['diferenca']==0 else "Erro")
