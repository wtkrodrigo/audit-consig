import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- ESTILO ---
st.set_page_config(page_title="RRB", layout="wide")
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; 
    border-radius: 10px; border-left: 5px solid #002D62; 
    box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>""", unsafe_allow_html=True)

# --- DB ---
try:
    u = st.secrets["SUPABASE_URL"]
    k = st.secrets["SUPABASE_KEY"]
    sb = create_client(u, k)
except:
    st.error("Erro Secrets"); st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.title("🛡️ RRB")
m = st.sidebar.radio("Menu", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# --- 1. FUNCIONARIO ---
if m == "👤 Func":
    st.subheader("🔎 Consulta")
    cpf = st.text_input("CPF")
    c = "".join(filter(str.isdigit, cpf))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq(
            "cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id')==ct]
            pg, tt = len(hist), int(d.get('parcelas_total', 0))
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Banco", d.get('banco_nome'))
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Erro")
            if tt > 0: st.progress(min(1.0, pg/tt))

# --- 2. EMPRESA ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_in = st.text_input("Login")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login",u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
    else:
        st.subheader(f"🏢 {st.session_state.n}")
        if st.sidebar.button("SAIR"):
            st.session_state.at = False; st.rerun()

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
                        pld = {
                            "nome_empresa": st.session_state.n,
                            "cpf": str(r['cpf']),
                            "nome_funcionario": str(r['nome']),
                            "valor_rh": vr, "valor_banco": vb,
                            "diferenca": vr - vb,
                            "banco_nome": str(r.get('banco', 'N/A')),
                            "contrato_id": str(r.get('contrato', 'N/A')),
                            "parcelas_total": tp,
                            "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_auditoria").insert(pld).execute()
                    st.success("✅ OK!")
                except Exception as e: st.error(f"Erro: {e}")

        st.markdown("---")
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).execute()
        if res.data:
            f_df = pd.DataFrame(res.data)
            v_list = []
            for i, row in f_df.head(20).iterrows():
                p_pg = len(f_df[f_df['contrato_id'] == row['contrato_id']])
                v_list.append({
                    "Nome": row['nome_funcionario'],
                    "Banco": row['banco_nome'],
                    "Contrato": row['contrato_id'],
                    "Dif": f"R$ {row['diferenca']:.2f}",
                    "Pagas": p_pg,
                    "Faltam": max(0, int(row['parcelas_total']) - p_pg)
                })
            st.table(pd.DataFrame(v_list))

# --- 3. ADMIN ---
elif m == "⚙️ Admin":
    st.subheader("⚙️ Cadastro")
    pw = st.text_input("Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            rs = st.text_input("Razão Social")
            cj = st.text_input("CNPJ")
            rp = st.text_input("Representante")
            tl = st.text_input("Telefone")
            en = st.text_input("Endereço")
            us = st.text_input("Login")
            sn = st.text_input("Senha", type='password')
            lk = st.text_input("Link CSV")
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now()+timedelta(30)).isoformat()
                di = {
                    "nome_empresa": rs, "cnpj": cj, 
                    "representante": rp, "telefone": tl, 
                    "endereco": en, "login": us, "senha": h(sn), 
                    "data_expiracao": v, "link_planilha": lk
                }
                sb.table("empresas").insert(di).execute()
                st.success("Cadastrado!")
