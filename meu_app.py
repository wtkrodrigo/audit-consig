import streamlit as st
import pandas as pd
import sqlite3
import hashlib

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="AuditConsig SaaS", layout="wide")

# Função para criar o banco de dados e as tabelas
def init_db():
    conn = sqlite3.connect('usuarios_empresas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS empresas 
                 (id INTEGER PRIMARY KEY, nome_empresa TEXT, login TEXT, senha TEXT)''')
    conn.commit()
    conn.close()

# Função para criptografar senha (segurança básica)
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

init_db()

# --- INTERFACE DE LOGIN ---
st.sidebar.title("🔐 Acesso Restrito")
menu_login = st.sidebar.selectbox("Menu", ["Login Cliente", "Admin (Cadastrar Empresa)"])

if menu_login == "Admin (Cadastrar Empresa)":
    st.subheader("Painel Administrativo - Cadastro de Novos Clientes")
    senha_master = st.text_input("Senha Mestre", type='password')
    
    if senha_master == st.secrets["SENHA_MASTER"]: # Altere esta senha mestre
        nova_empresa = st.text_input("Nome da Empresa")
        novo_login = st.text_input("Login para o RH")
        nova_senha = st.text_input("Senha para o RH", type='password')
        
        if st.button("Cadastrar Empresa"):
            conn = sqlite3.connect('usuarios_empresas.db')
            c = conn.cursor()
            c.execute('INSERT INTO empresas(nome_empresa, login, senha) VALUES (?,?,?)', 
                      (nova_empresa, novo_login, make_hashes(nova_senha)))
            conn.commit()
            conn.close()
            st.success(f"Empresa {nova_empresa} cadastrada com sucesso!")
    elif senha_master:
        st.error("Senha Mestre incorreta.")

elif menu_login == "Login Cliente":
    st.sidebar.subheader("Login do RH")
    user = st.sidebar.text_input("Usuário")
    passwd = st.sidebar.text_input("Senha", type='password')
    
    # Lógica de Autenticação
    conn = sqlite3.connect('usuarios_empresas.db')
    c = conn.cursor()
    c.execute('SELECT senha, nome_empresa FROM empresas WHERE login = ?', (user,))
    result = c.fetchone()
    conn.close()

    if result and check_hashes(passwd, result[0]):
        st.sidebar.success(f"Conectado: {result[1]}")
        
        # --- AQUI ENTRA SUA FERRAMENTA DE AUDITORIA ---
        st.title(f"🛡️ Painel de Auditoria - {result[1]}")
        
        col1, col2 = st.columns(2)
        arquivo_rh = col1.file_uploader("Upload Folha de Pagamento (CSV)", type=['csv'])
        arquivo_banco = col2.file_uploader("Upload Relatório do Banco (CSV)", type=['csv'])

        if arquivo_rh and arquivo_banco:
            df_rh = pd.read_csv(arquivo_rh)
            df_banco = pd.read_csv(arquivo_banco)
            
            try:
                df_final = pd.merge(df_rh, df_banco, on='cpf')
                df_final['Divergência'] = df_final['parcela_atual'] > df_final['total_parcelas']
                
                st.write("### Resultados da Auditoria")
                st.dataframe(df_final.style.apply(lambda x: ['background-color: #ffcccc' if x.Divergência else '' for _ in x], axis=1))
            except Exception as e:
                st.error("Erro: Verifique se as colunas 'cpf' existem em ambos os arquivos.")
    elif passwd:
        st.sidebar.error("Usuário ou Senha incorretos")
