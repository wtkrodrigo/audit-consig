import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES BÁSICAS ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

# --- DESIGN ---
st.markdown("<style>.main { background-color: #f8f9fa; } .stMetric { background: white; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }</style>", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- NAVEGAÇÃO ---
st.sidebar.title("🛡️ RRB-SOLUÇÕES")
menu = ["Portal do Funcionário", "Portal da Empresa", "Administração RRB"]
escolha = st.sidebar.selectbox("Selecione o Portal", menu)

# ---------------------------------------------------------
# 1. PORTAL DO FUNCIONÁRIO
# ---------------------------------------------------------
if escolha == "Portal do Funcionário":
    st.title("Área do Colaborador")
    cpf_input = st.text_input("Digite seu CPF (apenas números)")
    cpf_busca = "".join(filter(str.isdigit, cpf_input))
    
    if st.button("Consultar Meus Dados"):
        if cpf_busca:
            res = supabase.table("resultados_auditoria").select("*").eq("cpf", cpf_busca).order("data_processamento", desc=True).limit(1).execute()
            if res.data:
                d = res.data[0]
                st.subheader(f"Olá, {d['nome_funcionario']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Valor em Folha", f"R$ {d['valor_rh']}")
                c2.metric("Valor no Banco", f"R$ {d['valor_banco']}")
                c3.metric("Diferença", f"R$ {d['diferenca']}", delta=-d['diferenca'] if d['diferenca'] != 0 else None)
                if d['status'] == "✅ OK":
                    st.success("🎯 Seus descontos estão em conformidade.")
                else:
                    st.error(f"⚠️ Divergência de R$ {abs(d['diferenca'])} detectada. Procure o RH.")
            else:
                st.warning("Dados não localizados para este CPF.")
        else:
            st.warning("Informe o CPF.")

# ---------------------------------------------------------
# 2. PORTAL DA EMPRESA
# ---------------------------------------------------------
elif escolha == "Portal da Empresa":
    if 'emp_auth' not in st.session_state: st.session_state['emp_auth'] = False
    if not st.session_state['emp_auth']:
        st.subheader("Login Empresa")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data and check_hashes(p, q.data[0]['senha']):
                st.session_state['emp_auth'], st.session_state['emp_nome'] = True, q.data[0]['nome_empresa']
                st.rerun()
            else: st.error("Acesso Negado.")
    else:
        st.subheader(f"Painel: {st.session_state['emp_nome']}")
        f1, f2 = st.file_uploader("Folha RH", type=['csv']), st.file_uploader("Base Banco", type=['csv'])
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")
            st.dataframe(res)
            if st.button("🚀 PUBLICAR PARA FUNCIONÁRIOS"):
                for _, r in res.iterrows():
                    payload = {"nome_empresa": st.session_state['emp_nome'], "cpf": str(r['cpf']), "nome_funcionario": r['nome'], "valor_rh": float(r['valor_descontado_rh']), "valor_banco": float(r['valor_devido_banco']), "diferenca": float(r['Diferença']), "status": r['Status']}
                    supabase.table("resultados_auditoria").insert(payload).execute()
                st.success("Publicado!")

# ---------------------------------------------------------
# 3. ADMINISTRAÇÃO RRB
# ---------------------------------------------------------
elif escolha == "Administração RRB":
    st.subheader("Gestão Master")
    sm = st.text_input("Senha Master", type='password')
    if sm == st.secrets.get("SENHA_MASTER"):
        with st.form("cad_emp"):
            nome = st.text_input("Nome da Empresa")
            user = st.text_input("Login")
            senha = st.text_input("Senha", type='password')
            plano = st.selectbox("Plano", ["Bronze (30 dias)", "Prata (60 dias)", "Ouro (90 dias)"])
            if st.form_submit_button("CADASTRAR"):
                dias = 30 if "Bronze" in plano else 60 if "Prata" in plano else 90
                exp = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
                dados = {"nome_empresa": nome, "login": user, "senha": make_hashes(senha), "data_expiracao": exp
