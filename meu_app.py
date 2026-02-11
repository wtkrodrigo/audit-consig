import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.05);
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #002D62;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    @media (prefers-color-scheme: dark) { 
        .logo-text { color: #4A90E2; }
        [data-testid="stMetric"] { background-color: rgba(255, 255, 255, 0.05); }
    }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:var(--text-color); opacity: 0.6; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO SEGURA COM SUPABASE ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("Configurações (Secrets) do Supabase não encontradas."); st.stop()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if menu == "🏢 Empresa" and st.session_state.get('at'):
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Sair da Sessão"):
        logout()

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para liberar a consulta.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                if str(dt_nasc_in) == str(d.get("data_nascimento", "")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Bem-vindo, {d['nome_funcionario']}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Banco", d.get('banco_nome', 'N/A'))
                    stt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status", stt)
                    with st.expander("📊 Detalhes do Contrato"):
                        st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f} | **ID:** {d.get('contrato_id', 'N/A')}")
                        pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                        st.write(f"**Parcelas:** {pp} de {pt}")
                        if pt > 0: st.progress(min(pp/pt, 1.0))
                else: st.error("Dados de validação incorretos.")
            else: st.warning("CPF não localizado.")
        except Exception as e: st.error(f"Erro na consulta: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    
    if 'at' not in st.session_state: st.session_state.at = False
    if 'reset_mode' not in st.session_state: st.session_state.reset_mode = False
    
    if not st.session_state.at:
        if not st.session_state.reset_mode:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type='password')
            if st.button("ACESSAR", use_container_width=True):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Login ou senha inválidos.")
            if st.button("Esqueci minha senha"):
                st.session_state.reset_mode = True; st.rerun()
        else:
            st.subheader("🔑 Recuperar Senha")
            user_reset = st.text_input("Confirme seu Usuário")
            cnpj_reset = st.text_input("Confirme o CNPJ (apenas números)")
            nova_senha = st.text_input("Nova Senha", type="password")
            c_res1, c_res2 = st.columns(2)
            if c_res1.button("ATUALIZAR SENHA", use_container_width=True):
                check = sb.table("empresas").select("*").eq("login", user_reset).eq("cnpj", cnpj_reset).execute()
                if check.data:
                    sb.table
