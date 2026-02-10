import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Auditoria Pro", layout="wide", page_icon="🛡️")

# --- DESIGN PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main { background-color: #f0f2f6; }
    
    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    
    .shield-icon {
        background: linear-gradient(135deg, #002D62 0%, #d90429 100%);
        color: white;
        padding: 15px;
        border-radius: 12px;
        margin-right: 15px;
        font-size: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .logo-text { font-weight: 800; font-size: 32px; color: #002D62; margin: 0; }
    .logo-sub { color: #d90429; }

    div.stButton > button:first-child {
        background: #002D62;
        color: white;
        border-radius: 10px;
        border: none;
        height: 3.2em;
        font-weight: 700;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background: #d90429;
    }

    .stTextInput > div > div > input { border-radius: 10px !important; }
    
    .audit-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #002D62;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- FUNÇÕES DE SEGURANÇA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- CABEÇALHO ---
st.markdown("""
    <div class="header-container">
        <div class="shield-icon">🛡️</div>
        <div>
            <p class="logo-text">RRB-<span class="logo-sub">SOLUÇÕES</span></p>
            <p style="margin:0; font-size:12px; color:gray; font-weight:bold; letter-spacing:1px;">AUDITORIA INTELIGENTE</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- ESTADO DA SESSÃO ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- NAVEGAÇÃO ---
opcao = st.sidebar.selectbox("Escolha o Portal", ["Login Cliente", "Portal Administrador"])

# --- PORTAL ADMINISTRADOR ---
if opcao == "Portal Administrador":
    st.markdown('<div class="audit-card"><h4>🛠️ Cadastro de Empresas</h4></div>', unsafe_allow_html=True)
    senha_master = st.text_input("Senha Master", type='password')
    
    if senha_master == st.secrets["SENHA_MASTER"]:
        with st.form("admin_form"):
            n_emp = st.text_input("Nome da Empresa")
            l_emp = st.text_input("Login")
            s_emp = st.text_input("Senha", type='password')
            if st.form_submit_button("CADASTRAR"):
                if n_emp and l_emp and s_emp:
                    dados = {"nome_empresa": n_emp, "login": l_emp, "senha": make_hashes(s_emp)}
                    supabase.table("empresas").insert(dados).execute()
                    st.success("✅ Empresa registrada!")

# --- PORTAL CLIENTE ---
elif opcao == "Login Cliente":
    if not st.session_state['autenticado']:
        st.markdown('<div class="audit-card"><h4>🔐 Acesso do Cliente</h4></div>', unsafe_allow_html=True)
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data and check_hashes(p, q.data[0]['senha']):
                st.session_state['autenticado'] = True
                st.session_state['empresa_nome'] = q.data[0]['nome_empresa']
                st.rerun()
            else:
                st.error("Login inválido.")

    if st.session_state['autenticado']:
        st.sidebar.button("Encerrar Sessão", on_click=lambda: st.session_state.update({"autenticado": False}))
        st.markdown(f"### 📊 Painel: {st.session_state['empresa_nome']}")
        
        st.markdown('<div class="audit-card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        f1 = c1.file_uploader("Base RH (CSV)", type=['csv'])
        f2 = c2.file_uploader("Base Banco (CSV)", type=['csv'])
        st.markdown('</div>', unsafe_allow_html=True)

        if f1 and f2:
            try:
                df1 = pd.read_csv(f1)
                df2 = pd.read_csv(f2)
                df_res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
                st.write("#### ✅ Resultado")
                st.dataframe(df_res, use_container_width=True)
                csv = df_res.to_csv(index=False).encode('utf-8')
                st.download_button("💾 BAIXAR RELATÓRIO", csv, "auditoria.csv", "text/csv")
            except Exception as e:
                st.error(f"Erro: Verifique a coluna 'cpf'. {e}")
