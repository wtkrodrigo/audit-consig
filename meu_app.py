import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Gestão Pro", layout="wide", page_icon="🛡️")

# --- DESIGN (CSS) ---
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
            <p style="margin:0; font-size:12px; color:gray; font-weight:bold; letter-spacing:1px;">SISTEMA ANTI-BLOQUEIO</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

menu = ["Login Cliente", "Portal Administrador"]
escolha = st.sidebar.selectbox("Navegação", menu)

# --- PORTAL ADMINISTRADOR ---
if escolha == "Portal Administrador":
    st.subheader("🛠️ Gestão de Planos e Clientes")
    senha_master = st.text_input("Senha Master", type='password')
    
    if senha_master == st.secrets["SENHA_MASTER"]:
        with st.form("cadastro_detalhado"):
            st.write("### Novo Contrato")
            c1, c2 = st.columns(2)
            nome = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            
            plano = st.selectbox("Selecione o Plano", [
                "Bronze - R$ 250 (1 Mês)", 
                "Prata - R$ 350 (2 Meses)", 
                "Ouro - R$ 500 (1 Mês)",
                "Teste - 1 Dia"
            ])
            
            st.write("### Acesso")
            user = c1.text_input("Usuário Login")
            pw = c2.text_input("Senha Inicial", type='password')
            
            if st.form_submit_button("ATIVAR E GERAR ACESSO"):
                if nome and user and pw:
                    # Lógica de expiração
                    hoje = datetime.now()
                    if "Bronze" in plano: expiracao = hoje + timedelta(days=30)
                    elif "Prata" in plano: expiracao = hoje + timedelta(days=60)
                    elif "Ouro" in plano: expiracao = hoje + timedelta(days=30)
                    else: expiracao = hoje + timedelta(days=1)
                    
                    dados = {
                        "nome_empresa": nome, "cnpj": cnpj,
                        "plano_mensal": plano, "login": user, 
                        "senha": make_hashes(pw),
                        "data_expiracao": expiracao.strftime("%Y-%m-%d")
                    }
                    supabase.table("empresas").insert(dados).execute()
                    st.success(f"✅ {nome} ativado até {expiracao.strftime('%d/%m/%Y')}!")
                else:
                    st.warning("Preencha os campos obrigatórios.")

# --- LOGIN E PORTAL CLIENTE ---
elif escolha == "Login Cliente":
    if not st.session_state['autenticado']:
        st.markdown('<div class="audit-card"><h4>🔐 Acesso do Cliente</h4></div>', unsafe_allow_html=True)
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        
        if st.button("ENTRAR"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            
            if q.data:
                dados_empresa = q.data[0]
                # VERIFICAÇÃO DE BLOQUEIO POR DATA
                data_exp = datetime.strptime(dados_empresa['data_expiracao'], "%Y-%m-%d")
                
                if datetime.now() > data_exp:
                    st.error("🚫 ACESSO BLOQUEADO! Seu plano expirou. Entre em contato com RRB-SOLUÇÕES para renovação.")
                elif check_hashes(p, dados_empresa['senha']):
                    st.session_state['autenticado'] = True
                    st.session_state['empresa_nome'] = dados_empresa['nome_empresa']
                    st.session_state['validade'] = data_exp.strftime("%d/%m/%Y")
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")

    if st.session_state['autenticado']:
        st.sidebar.info(f"Assinatura válida até: {st.session_state['validade']}")
        if st.sidebar.button("Sair"):
            st.session_state['autenticado'] = False
            st.rerun()

        st.markdown(f"### 📊 Painel de Auditoria - {st.session_state['empresa_nome']}")
        
        st.markdown('<div class="audit-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        f1 = col1.file_uploader("Folha RH (CSV)", type=['csv'])
        f2 = col2.file_uploader("Base Banco (CSV)", type=['csv'])
        st.markdown('</div>', unsafe_allow_html=True)

        if f1 and f2:
            try:
                df1 = pd.read_csv(f1)
                df2 = pd.read_csv(f2)
                res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
                
                if 'valor_descontado_rh' in res.columns and 'valor_devido_banco' in res.columns:
                    res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
                    res['Status'] = res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")
                
                st.dataframe(res, use_container_width=True)
                
                csv = res.to_csv(index=False).encode('utf-8')
                st.download_button(f"📥 Baixar Relatório", csv, f"Auditoria_{st.session_state['empresa_nome']}.csv", "text/csv")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
