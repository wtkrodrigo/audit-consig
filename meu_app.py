import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, date, timedelta

# 1. Configuração de Página deve ser SEMPRE a primeira função Streamlit
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

# 2. Importação Segura
try:
    from supabase import create_client
    from fpdf import FPDF
except ImportError as e:
    st.error(f"🚨 ERRO DE INSTALAÇÃO: A biblioteca '{e.name}' não foi encontrada. Verifique se o nome do arquivo no GitHub é exatamente 'requirements.txt' (tudo minúsculo).")
    st.stop()

# 3. Conexão Segura (Não trava a abertura da página)
def carregar_conexao():
    try:
        if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
            return None, "Configuração de Secrets (URL/KEY) ausente no painel do Streamlit."
        
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        # Cria o cliente apenas se os dados existirem
        client = create_client(url, key)
        return client, None
    except Exception as e:
        return None, str(e)

sb, erro_conexao = carregar_conexao()

# --- CSS E DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #0e1117; }
    .card { background: #1e2127; padding: 20px; border-radius: 10px; border: 1px solid #4a90e2; }
</style>
""", unsafe_allow_html=True)

# 4. Interface Principal
st.sidebar.title("🛡️ RRB Platinum")
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

if erro_conexao:
    st.warning(f"⚠️ O sistema abriu, mas o Banco de Dados está offline: {erro_conexao}")

# --- ABA FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    st.title("🛡️ Portal do Colaborador")
    st.write("Consulte sua auditoria e baixe seu demonstrativo.")
    
    col1, col2 = st.columns(2)
    cpf = col1.text_input("Seu CPF")
    nasc = col2.date_input("Nascimento", value=date(2000,1,1))
    
    if st.button("ANALISAR AGORA", use_container_width=True):
        if not sb:
            st.error("Não é possível pesquisar sem conexão com o banco.")
        else:
            # Busca simples para testar
            try:
                res = sb.table("resultados_auditoria").select("*").eq("cpf", cpf.replace(".","").replace("-","")).execute()
                if res.data:
                    d = res.data[0]
                    st.success(f"Dados localizados para {d.get('nome_funcionario')}")
                    # Aqui entra a lógica dos cards e PDF...
                else:
                    st.warning("Nenhum registro encontrado para este CPF.")
            except Exception as e:
                st.error(f"Erro na busca: {e}")

# --- ABA EMPRESA ---
elif menu == "🏢 Empresa":
    st.title("🏢 Painel Corporativo")
    st.info("Área em manutenção para implementação Enterprise.")

# --- ABA ADMIN ---
else:
    st.title("⚙️ Admin Master")
    senha = st.text_input("Chave Mestre", type="password")
    if senha == st.secrets.get("SENHA_MASTER", "admin123"):
        st.write("Acesso Autorizado.")
    else:
        st.info("Insira a chave para gerenciar empresas.")

st.sidebar.markdown("---")
st.sidebar.caption("v2.1.0 Platinum Edition")
