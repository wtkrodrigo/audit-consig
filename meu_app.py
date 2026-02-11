import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide")

# --- CONEXÃO ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nos Secrets.")
    st.stop()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- MENU ---
menu = ["Portal do Funcionário", "Portal da Empresa", "Administração RRB"]
escolha = st.sidebar.selectbox("Módulo", menu)

# 1. FUNCIONÁRIO
if escolha == "Portal do Funcionário":
    st.title("🛡️ Área do Colaborador")
    cpf_input = st.text_input("CPF (apenas números)")
    cpf = "".join(filter(str.isdigit, cpf_input))
    
    if st.button("Consultar"):
        if cpf:
            res = supabase.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
            if res.data:
                d = res.data[0]
                st.subheader(f"Olá, {d['nome_funcionario']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Folha RH", f"R$ {d['valor_rh']}")
                c2.metric("Banco", f"R$ {d['valor_banco']}")
                c3.metric("Diferença", f"R$ {d['diferenca']}")
                if d['status'] == "✅ OK": st.success("Tudo certo!")
                else: st.error("Divergência detectada!")
            else: st.warning("Não encontrado.")

# 2. EMPRESA
elif escolha == "Portal da Empresa":
    if 'emp_auth' not in st.session_state: st.session_state['emp_auth'] = False
    if not st.session_state['emp_auth']:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("Login"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data and check_hashes(p, q.data[0]['senha']):
                st.session_state['emp_auth'], st.session_state['emp_nome'] = True, q.data[0]['nome_empresa']
                st.rerun()
    else:
        st.title(f"Empresa: {st.session_state['emp_nome']}")
        f1, f2 = st.file_uploader("RH"), st.file_uploader("Banco")
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf')
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "✅ OK" if x == 0 else "❌ ERRO")
            st.dataframe(res)
            if st.button("🚀 PUBLICAR"):
                for _, r in res.iterrows():
                    payload = {
                        "nome_empresa": st.session_state['emp_nome'],
                        "cpf": str(r['cpf']),
                        "nome_funcionario": r['nome'],
                        "valor_rh": float(r['valor_descontado_rh']),
                        "valor_banco": float(r['valor_devio_banco']),
                        "diferenca": float(r['Diferença']),
                        "status": r['Status']
                    }
                    supabase.table("resultados_auditoria").insert(payload).execute()
                st.success("Publicado!")

# 3. ADMIN
elif escolha == "Administração RRB":
    sm = st.text_input("Master", type='password')
    if sm == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            n = st.text_input("Empresa")
            l = st.text_input("Login")
            s = st.text_input("Senha", type='password')
            pl = st.selectbox("Plano", [30, 60, 90])
            if st.form_submit_button("Cadastrar"):
                exp = (datetime.now() + timedelta(days=pl)).strftime("%Y-%m-%d")
                dados_emp = {
                    "nome_empresa": n,
                    "login": l,
                    "senha": make_hashes(s),
                    "data_expiracao": exp,
                    "plano_mensal": str(pl)
                }
                supabase.table("empresas").insert(dados_emp).execute()
                st.success("OK!")
