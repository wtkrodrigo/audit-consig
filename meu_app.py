import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Admin", layout="wide", page_icon="🛡️")

# --- DESIGN PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main { background-color: #f0f2f6; }
    .header-container {
        display: flex; align-items: center; justify-content: center;
        padding: 20px; background: white; border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 25px;
    }
    .shield-icon {
        background: linear-gradient(135deg, #002D62 0%, #d90429 100%);
        color: white; padding: 15px; border-radius: 12px; margin-right: 15px; font-size: 30px;
    }
    .logo-text { font-weight: 800; font-size: 32px; color: #002D62; margin: 0; }
    .logo-sub { color: #d90429; }
    div.stButton > button:first-child {
        background: #002D62; color: white; border-radius: 10px; width: 100%; font-weight: 700;
    }
    div.stButton > button:first-child:hover { background: #d90429; }
    .audit-card {
        background: white; padding: 20px; border-radius: 15px;
        border-left: 5px solid #002D62; margin-bottom: 20px;
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
            <p style="margin:0; font-size:12px; color:gray; font-weight:bold; letter-spacing:1px;">GESTÃO DE CONTRATOS</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

opcao = st.sidebar.selectbox("Escolha o Portal", ["Login Cliente", "Portal Administrador"])

# --- PORTAL ADMINISTRADOR (COM NOVOS CAMPOS) ---
if opcao == "Portal Administrador":
    st.markdown('<div class="audit-card"><h4>🛠️ Cadastro Detalhado de Empresa</h4></div>', unsafe_allow_html=True)
    senha_master = st.text_input("Senha Master", type='password')
    
    if senha_master == st.secrets["SENHA_MASTER"]:
        with st.form("admin_form"):
            st.write("##### 📋 Dados Cadastrais")
            col1, col2 = st.columns(2)
            n_emp = col1.text_input("Nome da Empresa / Razão Social")
            cnpj_emp = col2.text_input("CNPJ")
            
            rep_emp = col1.text_input("Representante Legal")
            tel_emp = col2.text_input("Telefone de Contato")
            
            end_emp = st.text_input("Endereço Completo")
            
            st.write("##### 💰 Configurações de Acesso e Plano")
            col3, col4 = st.columns(2)
            l_emp = col3.text_input("Login de Usuário")
            s_emp = col3.text_input("Senha Inicial", type='password')
            
            plano_emp = col4.selectbox("Plano Mensal", ["Bronze - R$ 299", "Prata - R$ 599", "Ouro - R$ 999", "Personalizado"])
            
            if st.form_submit_button("CADASTRAR E ATIVAR CONTRATO"):
                if n_emp and l_emp and s_emp:
                    dados = {
                        "nome_empresa": n_emp, 
                        "cnpj": cnpj_emp,
                        "representante": rep_emp,
                        "telefone": tel_emp,
                        "endereco": end_emp,
                        "plano_mensal": plano_emp,
                        "login": l_emp, 
                        "senha": make_hashes(s_emp)
                    }
                    try:
                        supabase.table("empresas").insert(dados).execute()
                        st.success(f"✅ Empresa {n_emp} cadastrada com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("Nome, Login e Senha são obrigatórios.")

# --- PORTAL CLIENTE (LOGIN E AUDITORIA) ---
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
        st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"autenticado": False}))
        st.markdown(f"### 📊 Painel de Auditoria: {st.session_state['empresa_nome']}")
        
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
                st.write("#### ✅ Divergências Encontradas")
                st.dataframe(df_res, use_container_width=True)
                csv = df_res.to_csv(index=False).encode('utf-8')
                st.download_button("💾 BAIXAR RELATÓRIO", csv, "auditoria_rrb.csv", "text/csv")
            except Exception as e:
                st.error("Erro no processamento. Verifique a coluna 'cpf'.")
