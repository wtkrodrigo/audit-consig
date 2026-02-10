import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="AuditConsig Pro", layout="wide", page_icon="🛡️")

# --- CONEXÃO COM SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Erro ao carregar as credenciais do Supabase nos Secrets. Verifique o painel do Streamlit.")
    st.stop()

# --- FUNÇÕES DE SEGURANÇA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'empresa_nome' not in st.session_state:
    st.session_state['empresa_nome'] = None

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.title("🔐 Menu de Acesso")
opcao = st.sidebar.selectbox("Escolha o Portal", ["Login Cliente", "Portal Administrador"])

# --- PORTAL DO ADMINISTRADOR ---
if opcao == "Portal Administrador":
    st.header("🏢 Painel Administrativo")
    st.subheader("Cadastrar Novo Cliente")
    
    senha_master_input = st.text_input("Senha Master", type='password')
    
    if senha_master_input == st.secrets["SENHA_MASTER"]:
        with st.form("form_cadastro_empresa"):
            nome_emp = st.text_input("Nome da Empresa")
            login_emp = st.text_input("Login (Usuário)")
            senha_emp = st.text_input("Senha", type='password')
            submit = st.form_submit_button("Salvar Empresa no Supabase")
            
            if submit:
                if nome_emp and login_emp and senha_emp:
                    dados = {
                        "nome_empresa": nome_emp,
                        "login": login_emp,
                        "senha": make_hashes(senha_emp)
                    }
                    try:
                        # GRAVA NO BANCO DE DADOS EM NUVEM
                        supabase.table("empresas").insert(dados).execute()
                        st.success(f"✅ Sucesso! A empresa {nome_emp} agora está na nuvem.")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco: {e}")
                else:
                    st.warning("Preencha todos os campos corretamente.")
    elif senha_master_input:
        st.error("Senha Master incorreta.")

# --- PORTAL DO CLIENTE (LOGIN) ---
elif opcao == "Login Cliente":
    if not st.session_state['autenticado']:
        st.sidebar.subheader("Login do RH")
        usuario = st.sidebar.text_input("Usuário")
        senha_login = st.sidebar.text_input("Senha", type='password')
        
        if st.sidebar.button("Entrar"):
            try:
                # BUSCA A EMPRESA NO SUPABASE PELO LOGIN
                query = supabase.table("empresas").select("*").eq("login", usuario).execute()
                
                if query.data and check_hashes(senha_login, query.data[0]['senha']):
                    st.session_state['autenticado'] = True
                    st.session_state['empresa_nome'] = query.data[0]['nome_empresa']
                    st.rerun()
                else:
                    st.sidebar.error("Usuário ou senha inválidos.")
            except Exception as e:
                st.sidebar.error(f"Erro de conexão: {e}")
    
    # --- ÁREA LOGADA DO CLIENTE ---
    if st.session_state['autenticado']:
        st.title(f"🛡️ Painel de Auditoria - {st.session_state['empresa_nome']}")
        
        if st.sidebar.button("Sair"):
            st.session_state['autenticado'] = False
            st.rerun()

        st.write("Suba os arquivos para realizar o cruzamento de dados.")
        
        col1, col2 = st.columns(2)
        arq1 = col1.file_uploader("Arquivo da Empresa (CSV)", type=['csv'])
        arq2 = col2.file_uploader("Arquivo do Banco (CSV)", type=['csv'])

        if arq1 and arq2:
            try:
                df1 = pd.read_csv(arq1)
                df2 = pd.read_csv(arq2)
                
                # Exemplo de cruzamento por CPF
                df_cruzado = pd.merge(df1, df2, on='cpf', suffixes=('_empresa', '_banco'))
                st.write("### Resultados da Auditoria")
                st.dataframe(df_cruzado)
                
                csv = df_cruzado.to_csv(index=False).encode('utf-8')
                st.download_button("Baixar Resultado (CSV)", csv, "auditoria.csv", "text/csv")
                
            except Exception as error:
                st.error(f"Erro ao processar arquivos: {error}")
