import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RRB Auditoria", layout="wide", initial_sidebar_state="expanded")

# Estilos CSS para melhorar o visual
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .logo-text { font-size: 26px; font-weight: bold; color: #002D62; margin-bottom: 20px; }
</style>""", unsafe_allow_html=True)

def logo():
    st.markdown("<div class='logo-text'>🛡️ RRB SOLUÇÕES AUDITORIA</div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO SUPABASE ---
try:
    su = st.secrets["SUPABASE_URL"]
    sk = st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except Exception as e:
    st.error("Erro ao carregar credenciais do Supabase. Verifique os Secrets.")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.title("MENU PRINCIPAL")
menu = st.sidebar.radio("Ir para:", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- MÓDULO 1: FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    logo()
    cpf_raw = st.text_input("Informe seu CPF (apenas números)")
    cpf_clean = "".join(filter(str.isdigit, cpf_raw))
    
    if st.button("CONSULTAR AUDITORIA") and cpf_clean:
        res = sb.table("resultados_auditoria").select("*").eq("cpf", cpf_clean).execute()
        if res.data:
            # Pega o registro mais recente
            dados = res.data[-1]
            st.success(f"Bem-vindo(a), {dados['nome_funcionario']}")
            
            c1, c2, c3 = st.columns(3)
            val_rh = dados.get('valor_rh', 0)
            val_bc = dados.get('valor_banco', 0)
            diff = dados.get('diferenca', 0)
            
            c1.metric("Mensalidade (RH)", f"R$ {val_rh:,.2f}")
            c2.metric("Banco", dados.get('banco_nome', 'N/A'))
            c3.metric("Status Auditoria", "✅ OK" if diff == 0 else "❌ Divergência")
            
            with st.expander("Ver Detalhes do Contrato"):
                st.write(f"**Contrato:** {dados.get('contrato_id', 'N/A')}")
                st.write(f"**Parcelas Totais:** {dados.get('parcelas_total', 0)}")
                if diff != 0:
                    st.warning(f"Atenção: Identificamos uma diferença de R$ {diff:,.2f} entre o RH e o Banco.")
        else:
            st.warning("CPF não localizado. Entre em contato com o RH da sua empresa.")

# --- MÓDULO 2: EMPRESA ---
elif menu == "🏢 Empresa":
    logo()
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        u_in = st.text_input("Usuário Empresa")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            query = sb.table("empresas").select("*").eq("login", u_in).execute()
            if query.data and h(p_in) == query.data[0]['senha']:
                st.session_state.autenticado = True
                st.session_state.nome_emp = query.data[0]['nome_empresa']
                st.session_state.url_planilha = query.data[0].get('link_planilha')
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    else:
        st.subheader(f"Painel de Gestão: {st.session_state.nome_emp}")
        if st.sidebar.button("LOGOUT"): 
            st.session_state.autenticado = False
            st.rerun()
