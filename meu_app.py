import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Auditoria", layout="wide", page_icon="⚙️")

# --- DESIGN PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    /* Estilização Geral */
    .main { background-color: #f8f9fa; }
    
    /* Logo RRB-SOLUÇÕES */
    .logo-text {
        font-weight: 800; font-size: 35px; color: #0047AB; font-family: 'Arial';
    }
    .logo-sub { color: #FF0000; }
    
    /* Botões Arredondados */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #0047AB;
        color: white;
        border: none;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #FF0000;
        color: white;
        transform: scale(1.02);
    }
    
    /* Inputs Arredondados */
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
    
    /* Boxes de Sucesso e Erro */
    .stAlert {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception:
    st.error("Erro nas credenciais do Supabase nos Secrets.")
    st.stop()

# --- FUNÇÕES DE SEGURANÇA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- CABEÇALHO COM LOGO ---
st.markdown('<p class="logo-text">RRB-<span class="logo-sub">SOLUÇÕES</span> ⚙️</p>', unsafe_allow_html=True)
st.markdown("---")

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- NAVEGAÇÃO LATERAL ---
opcao = st.sidebar.selectbox("📋 Menu Principal", ["Login Cliente", "Portal Administrador"])

# --- PORTAL DO ADMINISTRADOR ---
if opcao == "Portal Administrador":
    st.subheader("🛠️ Gestão de Clientes")
    senha_master_input = st.text_input("Senha Master", type='password')
    
    if senha_master_input == st.secrets["SENHA_MASTER"]:
        with st.form("form_cadastro"):
            nome_emp = st.text_input("Nome da Empresa")
            login_emp = st.text_input("Login de Acesso")
            senha_emp = st.text_input("Senha Temporária", type='password')
            submit = st.form_submit_button("CADASTRAR EMPRESA")
            
            if submit:
                if nome_emp and login_emp and senha_emp:
                    dados = {"nome_empresa": nome_emp, "login": login_emp, "senha": make_hashes(senha_emp)}
                    supabase.table("empresas").insert(dados).execute()
                    st.success(f"✅ {nome_emp} cadastrada com sucesso!")
                else:
                    st.warning("Preencha todos os campos.")

# --- PORTAL DO CLIENTE ---
elif opcao == "Login Cliente":
    if not st.session_state['autenticado']:
        st.subheader("🔐 Acesso Restrito ao RH")
        col_l, col_r = st.columns(2)
        with col_l:
            usuario = st.text_input("Usuário")
            senha_login = st.text_input("Senha", type='password')
            if st.button("ENTRAR NO SISTEMA"):
                query = supabase.table("empresas").select("*").eq("login", usuario).execute()
                if query.data and check_hashes(senha_login, query.data[0]['senha']):
                    st.session_state['autenticado'] = True
                    st.session_state['empresa_nome'] = query.data[0]['nome_empresa']
                    st.rerun()
                else:
                    st.error("Credenciais incorretas.")
    
    if st.session_state['autenticado']:
        st.title(f"📊 Painel: {st.session_state['empresa_nome']}")
        if st.sidebar.button("Sair"):
            st.session_state['autenticado'] = False
            st.rerun()

        st.markdown("### 📑 Nova Auditoria")
        c1, c2 = st.columns(2)
        arq1 = c1.file_uploader("Arquivo RH (CSV)", type=['csv'])
        arq2 = c2.file_uploader("Arquivo Banco (CSV)", type=['csv'])

        if arq1 and arq2:
            try:
                df1 = pd.read_csv(arq1)
                df2 = pd.read_csv(arq2)
                df_cruzado = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
                
                st.write("#### Resultado do Cruzamento")
                st.dataframe(df_cruzado.style.set_properties(**{'border-radius': '10px'}))
                
                csv = df_cruzado.to_csv(index=False).encode('utf-8')
                st.download_button("📥 BAIXAR RELATÓRIO", csv, "auditoria_rrb.csv", "text/csv")
            except Exception as e:
                st.error(f"Erro nos arquivos: {e}")
