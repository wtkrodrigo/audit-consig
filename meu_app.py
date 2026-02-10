import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="AuditConsig Pro", layout="wide", page_icon="🛡️")

# --- CONEXÃO COM SUPABASE ---
# Puxa automaticamente das configurações de 'Secrets' do Streamlit Cloud
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Erro ao carregar as credenciais do Supabase nos Secrets.")
    st.stop()

# --- FUNÇÕES DE SEGURANÇA (Criptografia de Senha) ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- ESTADO DA SESSÃO (Mantém o usuário logado) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'empresa_nome' not in st.session_state:
    st.session_state['empresa_nome'] = None

# --- BARRA LATERAL (Navegação) ---
st.sidebar.title("🔐 Acesso ao Sistema")
opcao = st.sidebar.selectbox("Selecione o Portal", ["Login Cliente", "Portal Administrador"])

# --- LÓGICA DO PORTAL ADMINISTRADOR ---
if opcao == "Portal Administrador":
    st.header("🏢 Painel Administrativo")
    st.subheader("Cadastro de Novas Empresas Clientes")
    
    senha_master_input = st.text_input("Digite a Senha Master para liberar cadastro", type='password')
    
    if senha_master_input == st.secrets["SENHA_MASTER"]:
        st.success("Acesso Admin Liberado")
        
        with st.form("form_cadastro"):
            nome_emp = st.text_input("Nome da Empresa (Ex: RH Global)")
            login_emp = st.text_input("Login do Cliente (Ex: rh_global)")
            senha_emp = st.text_input("Senha do Cliente", type='password')
            botao_cadastrar = st.form_submit_button("Cadastrar Empresa na Nuvem")
            
            if botao_cadastrar:
                if nome_emp and login_emp and senha_emp:
                    dados = {
                        "nome_empresa": nome_emp,
                        "login": login_emp,
                        "senha": make_hashes(senha_emp)
                    }
                    try:
                        # GRAVA DIRETO NO SUPABASE
                        supabase.table("empresas").insert(dados).execute()
                        st.success(f"✅ Empresa '{nome_emp}' conectada e salva no Supabase!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                else:
                    st.warning("Preencha todos os campos.")
    elif senha_master_input:
        st.error("Senha Master incorreta.")

# --- LÓGICA DO LOGIN CLIENTE ---
elif opcao == "Login Cliente":
    if not st.session_state['autenticado']:
        st.sidebar.subheader("Login do RH")
        usuario = st.sidebar.text_input("Usuário")
        senha = st.sidebar.text_input("Senha", type='password')
        
        if st.sidebar.button("Entrar"):
            # BUSCA NO SUPABASE
            try:
                query = supabase.table("empresas").select("*").eq("login", usuario).execute()
                
                if query.data and check_hashes(senha, query.data[0]['senha']):
                    st.session_state['autenticado'] = True
                    st.session_state['empresa_nome'] = query.data[0]['nome_empresa']
                    st.rerun()
                else:
                    st.sidebar.error("Usuário ou senha inválidos.")
            except Exception as e:
                st.sidebar.error(f"Erro na conexão: {e}")
    
    # --- ÁREA LOGADA DO CLIENTE ---
    if st.session_state['autenticado']:
        st.title(f"🛡️ Auditoria Consignado - {st.session_state['empresa_nome']}")
        st.sidebar.info(f"Logado como: {st.session_state['empresa_nome']}")
        
        if st.sidebar.button("Sair / Logout"):
            st.session_state['autenticado'] = False
            st.rerun()

        st.info("Faça o upload dos arquivos abaixo para realizar a conferência.")
        
        col1, col2 = st.columns(2)
        arq_rh = col1.file_uploader("Folha de Pagamento (CSV)", type=['csv'])
        arq_banco = col2.file_uploader("Relatório do Banco (CSV)", type=['csv'])

        if arq_rh and arq_banco:
            df_rh = pd.read_csv(arq_rh
