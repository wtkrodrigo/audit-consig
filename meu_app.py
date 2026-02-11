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
m = st.sidebar.selectbox("Menu", 
    ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONARIO
if m == "👤 Func":
    st.subheader("🔎 Consulta")
    c_in = st.text_input("CPF (numeros)")
    c = "".join(filter(str.isdigit, c_in))
    if st.button("VERIFICAR") and c:
        r = sb.table("resultados_auditoria").select("*")
        r = r.eq("cpf", c).order("data_processamento").execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("RH", f"R$ {d['valor_rh']:.2f}")
            c2.metric("Banco", f"R$ {d['valor_banco']:.2f}")
            dif = d['diferenca']
            if dif == 0: st.info("✅ Correto")
            else: st.error(f"❌ Erro: R$ {abs(dif):.2f}")
        else: st.warning("Não encontrado")

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
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
            else: st.error("Erro login")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.button("🔄 ATUALIZAR DADOS"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                # Limpa registros antigos
                sb.table("resultados_auditoria").delete().eq(
                    "nome_empresa", st.session_state.n).execute()
                for _, r in df.iterrows():
                    v_rh = float(r['valor_rh'])
                    v_ba = float(r['valor_banco'])
                    pld = {
                        "nome_empresa": st.session_state.n,
                        "cpf": str(r['cpf']),
                        "nome_funcionario": r['nome'],
                        "valor_rh": v_rh,
                        "valor_banco": v_ba,
                        "diferenca": v_rh - v_ba,
                        "status": "OK" if v_rh == v_ba else "ERRO"
                    }
                    sb.table("resultados_auditoria").insert(pld).execute()
                st.success("✅ Sincronizado!")
                st.dataframe(df)
            except Exception as e:
                st.error(f"Erro: {e}")

# 3. ADMIN
elif m == "⚙️ Admin":
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            n = st.text_input("Empresa")
            cj = st.text_input("CNPJ")
            lk = st.text_input("Link CSV Planilha")
            u_c = st.text_input("Login Cliente")
            s_c = st.text_input("Senha Cliente", type='password')
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now()+timedelta(30)).strftime("%Y-%m-%d")
                d_i = {
                    "nome_empresa": n, "cnpj": cj,
                    "login": u_c, "senha": h(s_c),
                    "data_expiracao": v, "link_planilha": lk
                }
                sb.table("empresas").insert(d_i).execute()
                st.success(f"Ativo até {v}")
