import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f4f7f9; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; }
    .logo-container { display: flex; align-items: center; background: white; padding: 15px; border-radius: 15px; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .logo-rrb { font-weight: 900; font-size: 28px; color: #002D62; letter-spacing: -1px; }
    .logo-dot { color: #d90429; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="logo-container"><span class="logo-rrb">RRB<span class="logo-dot">.</span>SOLUÇÕES</span><span style="margin-left: 10px; color: gray; font-size: 10px;">🛡️ AUDITORIA DIGITAL</span></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()
def c_h(p, h_t): return h(p) == h_t

# --- NAVEGAÇÃO ---
menu = ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"]
m = st.sidebar.selectbox("Módulo", menu)

# 1. FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("Painel de Transparência")
    cpf_in = st.text_input("CPF (apenas números)")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("Consultar"):
        if cpf:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
            if r.data:
                d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}!")
                c1, c2, c3 = st.columns(3)
                c1.metric("Folha RH", f"R$ {d['valor_rh']}")
                c2.metric("Base Banco", f"R$ {d['valor_banco']}")
                c3.metric("Status", d['status'], delta=d['diferenca'] if d['diferenca']!=0 else None, delta_color="inverse")
            else: st.warning("Dados não localizados.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Acessar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and c_h(p, q.data[0]['senha']):
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']; st.rerun()
    else:
        st.subheader(f"Auditoria: {st.session_state.n}")
        f1, f2 = st.file_uploader("RH"), st.file_uploader("Banco")
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf')
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "✅ OK" if x == 0 else "❌ ERRO")
            st.dataframe(res)
            if st.button("🚀 PUBLICAR PARA COLABORADORES"):
                with st.spinner("Atualizando dados..."):
                    sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.n).execute()
                    for _, r in res.iterrows():
                        pl = {"nome_empresa": st.session_state.n, "cpf": str(r['cpf']), "nome_funcionario": r['nome'], "valor_rh": float(r['valor_descontado_rh']), "valor_banco": float(r['valor_devido_banco']), "diferenca": float(r['Diferença']), "status": r['Status']}
                        sb.table("resultados_auditoria").insert(pl).execute()
                st.success("Publicado com Sucesso!")

# 3. ADMIN
elif m == "⚙️ Admin":
    sm = st.text_input("Master", type='password')
    if sm == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            n, l, s = st.text_input("Empresa"), st.text_input("Login"), st.text_input("Senha", type='password')
            pl = st.selectbox("Plano (Dias)", [30, 60, 90])
            if st.form_submit_button("Cadastrar"):
                ex = (datetime.now() + timedelta(days=pl)).strftime("%Y-%m-%d")
                d_e = {"nome_empresa": n, "login": l, "senha": h(s), "data_expiracao": ex, "plano_mensal": str(pl)}
                sb.table("empresas").insert(d_e).execute()
                st.success(f"Empresa {n} cadastrada com sucesso!")
