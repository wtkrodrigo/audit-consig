import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Portal", layout="wide", page_icon="🛡️")

# --- DESIGN PERSONALIZADO ---
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
    .audit-card {
        background: white; padding: 20px; border-radius: 15px;
        border-left: 5px solid #002D62; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Erro nos Secrets do Supabase.")
    st.stop()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- CABEÇALHO ---
st.markdown(f"""
    <div class="header-container">
        <div class="shield-icon">🛡️</div>
        <div>
            <p class="logo-text">RRB-<span class="logo-sub">SOLUÇÕES</span></p>
            <p style="margin:0; font-size:12px; color:gray; font-weight:bold; letter-spacing:1px;">AUDITORIA E GESTÃO</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

menu = ["Login Cliente", "Portal Administrador"]
escolha = st.sidebar.selectbox("Navegação", menu)

# --- PORTAL ADMINISTRADOR ---
if escolha == "Portal Administrador":
    st.subheader("🛠️ Painel de Gestão RRB")
    senha_master = st.text_input("Senha Master", type='password')
    
    if senha_master == st.secrets["SENHA_MASTER"]:
        with st.form("cadastro_detalhado"):
            st.write("### Novo Contrato")
            c1, c2 = st.columns(2)
            nome = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            rep = c1.text_input("Representante Legal")
            tel = c2.text_input("Telefone")
            end = st.text_input("Endereço")
            
            st.write("### Acesso")
            user = c1.text_input("Usuário Login")
            pw = c2.text_input("Senha Inicial", type='password')
            plano = st.selectbox("Plano", ["Bronze", "Prata", "Ouro", "Personalizado"])
            
            if st.form_submit_button("CADASTRAR EMPRESA"):
                if nome and user and pw:
                    dados = {
                        "nome_empresa": nome, "cnpj": cnpj, "representante": rep,
                        "telefone": tel, "endereco": end, "plano_mensal": plano,
                        "login": user, "senha": make_hashes(pw)
                    }
                    supabase.table("empresas").insert(dados).execute()
                    st.success(f"Empresa {nome} ativada!")
                else:
                    st.warning("Preencha Nome, Usuário e Senha.")

# --- LOGIN E PORTAL CLIENTE ---
elif escolha == "Login Cliente":
    if not st.session_state['autenticado']:
        st.markdown('<div class="audit-card"><h4>🔐 Acesso do Cliente</h4></div>', unsafe_allow_html=True)
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data and check_hashes(p, q.data[0]['senha']):
                st.session_state['autenticado'] = True
                st.session_state['empresa_nome'] = q.data[0]['nome_empresa']
                st.rerun()
            else:
                st.error("Erro de login.")

    if st.session_state['autenticado']:
        st.sidebar.write(f"Logado como: **{st.session_state['empresa_nome']}**")
        if st.sidebar.button("Sair"):
            st.session_state['autenticado'] = False
            st.rerun()

        st.markdown(f"### 📊 Painel de Auditoria")
        
        st.markdown('<div class="audit-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        f1 = col1.file_uploader("Folha RH (CSV)", type=['csv'])
        f2 = col2.file_uploader("Base Banco (CSV)", type=['csv'])
        st.markdown('</div>', unsafe_allow_html=True)

        if f1 and f2:
            try:
                df1 = pd.read_csv(f1)
                df2 = pd.read_csv(f2)
                
                # Merge por CPF
                res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
                
                # Cálculos (Assume que as colunas nos CSVs de teste se chamam 'valor_descontado_rh' e 'valor_devido_banco')
                # Se os nomes forem diferentes, o pandas vai avisar.
                if 'valor_descontado_rh' in res.columns and 'valor_devido_banco' in res.columns:
                    res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
                    res['Status'] = res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")
                
                st.dataframe(res, use_container_width=True)
                
                # Botão de Download personalizado
                csv = res.to_csv(index=False).encode('utf-8')
                data_str = datetime.now().strftime("%d-%m-%Y")
                st.download_button(
                    f"📥 Baixar Relatório - {st.session_state['empresa_nome']}",
                    csv, 
                    f"Auditoria_{st.session_state['empresa_nome']}_{data_str}.csv",
                    "text/csv"
                )
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
