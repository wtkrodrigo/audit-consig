import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(
    page_title="Portal de Auditoria RRB", 
    layout="wide", 
    page_icon="🛡️"
)

# --- DESIGN E ESTILO ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stDataFrame { border-radius: 10px; }
    .divergente { color: #d90429; font-weight: bold; }
    .correto { color: #2a9d8f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- LÓGICA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- INTERFACE ---
if not st.session_state['autenticado']:
    st.title("🛡️ RRB-SOLUÇÕES | Login")
    with st.container():
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("Acessar Painel"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data and check_hashes(p, q.data[0]['senha']):
                st.session_state['autenticado'] = True
                st.session_state['user_data'] = q.data[0]
                st.rerun()
            else:
                st.error("Acesso negado.")

else:
    # CLIENTE LOGADO - SISTEMA COM NOME PRÓPRIO
    empresa = st.session_state['user_data']['nome_empresa']
    st.title(f"📊 Sistema de Auditoria - {empresa}")
    
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"autenticado": False}))

    # ÁREA DE DOWNLOAD DE MODELO (Para integração manual fácil)
    st.sidebar.markdown("---")
    st.sidebar.write("📂 **Modelos de Arquivo**")
    # Criando um modelo simples para o cliente baixar
    modelo_csv = pd.DataFrame(columns=['cpf', 'nome', 'valor']).to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Baixar Modelo CSV", modelo_csv, "modelo_rrb.csv", "text/csv")

    # PROCESSAMENTO
    st.info("Envie os arquivos CSV do mês para cruzamento automático.")
    col1, col2 = st.columns(2)
    f1 = col1.file_uploader("Base RH", type=['csv'])
    f2 = col2.file_uploader("Base Banco", type=['csv'])

    if f1 and f2:
        df1 = pd.read_csv(f1)
        df2 = pd.read_csv(f2)
        
        # MERGE E CÁLCULO DE DIVERGÊNCIA
        df_res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
        
        # Criando a coluna de diferença
        df_res['Diferença'] = df_res['valor_descontado_rh'] - df_res['valor_devido_banco']
        
        # Status
        df_res['Status'] = df_res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")

        st.subheader("📋 Relatório Analítico")
        st.dataframe(df_res.style.applymap(lambda x: 'color: red' if x == "❌ DIVERGENTE" else ('color: green' if x == "✅ OK" else ''), subset=['Status']), use_container_width=True)

        # DOWNLOAD COM NOME PRÓPRIO
        data_atual = datetime.now().strftime("%d_%m_%Y")
        nome_arquivo = f"Auditoria_{empresa.replace(' ', '_')}_{data_atual}.csv"
        
        csv_final = df_res.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Baixar Relatório: {nome_arquivo}",
            data=csv_final,
            file_name=nome_arquivo,
            mime="text/csv"
        )
