import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

# --- DESIGN ---
st.markdown("<style>.main { background-color: #f0f2f6; } .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; background-color: #002D62; color: white; }</style>", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro nos Secrets: {e}")
    st.stop()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

st.title("🛡️ RRB-SOLUÇÕES | Auditoria Pro")
st.write("---")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

menu = ["Login Cliente", "Portal Administrador"]
escolha = st.sidebar.selectbox("Módulo", menu)

if escolha == "Portal Administrador":
    st.subheader("🛠️ Gestão de Contratos")
    senha_master = st.text_input("Senha Master", type='password')
    
    if senha_master == st.secrets["SENHA_MASTER"]:
        with st.form("cadastro_empresa"):
            nome = st.text_input("Nome da Empresa")
            cnpj = st.text_input("CNPJ")
            plano = st.selectbox("Plano", ["Bronze - 1 Mês", "Prata - 2 Meses", "Ouro - 3 Meses", "Teste - 1 Dia"])
            user = st.text_input("Usuário")
            pw = st.text_input("Senha", type='password')
            
            if st.form_submit_button("CADASTRAR E ATIVAR"):
                if nome and user and pw:
                    hoje = datetime.now()
                    dias = 30 if "Bronze" in plano else 60 if "Prata" in plano else 90 if "Ouro" in plano else 1
                    expiracao = hoje + timedelta(days=dias)
                    
                    dados = {
                        "nome_empresa": nome, "cnpj": cnpj,
                        "plano_mensal": plano, "login": user, 
                        "senha": make_hashes(pw),
                        "data_expiracao": expiracao.strftime("%Y-%m-%d")
                    }
                    supabase.table("empresas").insert(dados).execute()
                    st.success(f"Ativado! Validade: {expiracao.strftime('%d/%m/%Y')}")

elif escolha == "Login Cliente":
    if not st.session_state['autenticado']:
        st.subheader("🔐 Acesso Restrito")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ENTRAR NO PAINEL"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data:
                d = q.data[0]
                
                # --- CORREÇÃO DO ERRO (STRPTIME ARGUMENT 1 MUST BE STR) ---
                raw_date = d.get('data_expiracao')
                if raw_date is None:
                    # Se não houver data, define uma data de hoje para obrigar renovação ou tratar erro
                    st.error("⚠️ Cadastro incompleto (sem data de validade). Contate o administrador.")
                else:
                    exp = datetime.strptime(raw_date, "%Y-%m-%d")
                    if datetime.now() > exp:
                        st.error(f"🚫 ACESSO BLOQUEADO! Plano expirou em {exp.strftime('%d/%m/%Y')}.")
                    elif check_hashes(p, d['senha']):
                        st.session_state['autenticado'] = True
                        st.session_state['empresa_nome'] = d['nome_empresa']
                        st.session_state['validade'] = exp.strftime("%d/%m/%Y")
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
            else:
                st.error("Usuário não cadastrado.")

    if st.session_state['autenticado']:
        st.sidebar.info(f"Empresa: {st.session_state['empresa_nome']}")
        st.sidebar.info(f"Assinatura até: {st.session_state['validade']}")
        if st.sidebar.button("Sair"):
            st.session_state['autenticado'] = False
            st.rerun()

        st.subheader(f"📊 Auditoria - {st.session_state['empresa_nome']}")
        c1, c2 = st.columns(2)
        f1 = c1.file_uploader("Subir Base RH (CSV)", type=['csv'])
        f2 = c2.file_uploader("Subir Base Banco (CSV)", type=['csv'])

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
                st.download_button("📥 Baixar Resultados", csv, "auditoria.csv", "text/csv")
            except Exception as e:
                st.error(f"Erro: {e}")
