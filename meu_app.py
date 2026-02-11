import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide")

st.markdown("""<style>
    .main { background: #f4f7f9; }
    .stMetric { background: white; padding: 20px; border-radius: 15px; border-left: 5px solid #002D62; }
    .logo-rrb { font-weight: 900; font-size: 30px; color: #002D62; text-align: center; padding: 20px; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="logo-rrb">RRB<span style="color:#d90429">.</span>SOLUÇÕES</div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()
def c_h(p, h_t): return h(p) == h_t

# --- MENU ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta")
    cpf_in = st.text_input("CPF (apenas números)")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR"):
        if cpf:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
            if r.data:
                d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
                c1, c2 = st.columns(2)
                c1.metric("Folha", f"R$ {d['valor_rh']}")
                c2.metric("Banco", f"R$ {d['valor_banco']}")
                if d['diferenca'] == 0: st.info("✅ Tudo ok")
                else: st.error(f"❌ Erro: R$ {abs(d['diferenca'])}")
            else: st.warning("Não achamos este CPF.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and c_h(p, q.data[0]['senha']):
                exp = datetime.strptime(q.data[0]['data_expiracao'], "%Y-%m-%d")
                if datetime.now() > exp: st.error("Expirado")
                else:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.rerun()
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        f1, f2 = st.file_uploader("RH"), st.file_uploader("Banco")
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf')
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "OK" if x == 0 else "ERRO")
            k1, k2 = st.columns(2)
            k1.metric("Total", len(res)); k2.metric("Erros", len(res[res['Status']=="ERRO"]))
            st.dataframe(res)
            if st.button("🚀 PUBLICAR"):
                sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.n).execute()
                for _, r in res.iterrows():
                    pl = {"nome_empresa": st.session_state.n, "cpf": str(r['cpf']), "nome_funcionario": r['nome'], "valor_rh": float(r['valor_descontado_rh']), "valor_banco": float(r['valor_devido_banco']), "diferenca": float(r['Diferença']), "status": r['Status']}
                    sb.table("resultados_auditoria").insert(pl).execute()
                st.success("OK!")

# 3. ADMIN
elif m == "⚙️ Admin":
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("c"):
            n, l, s = st.text_input("Empresa"), st.text_input("Login"), st.text_input("Senha", type='password')
            d = st.number_input("Dias", 1, 365, 30)
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
                sb.table("empresas").insert({"nome_empresa": n, "login": l, "senha": h(s), "data_expiracao": v}).execute()
                st.success(f"Ativo até {v}")
