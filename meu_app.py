import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd; }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Erro de conexão com o banco de dados. Verifique os Secrets.")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    cpf_in = st.text_input("Digite seu CPF (somente números)")
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Bem-vindo, {d.get('nome_funcionario', 'Usuário')}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
            c3.metric("Status", status)
            
            # Detalhamento de Parcelas
            t_parc = int(d.get('parcelas_total', 0))
            p_parc = int(d.get('parcelas_pagas', 0))
            r_parc = max(0, t_parc - p_parc)
            
            with st.expander("Detalhamento do Empréstimo", expanded=True):
                st.write(f"**Valor do Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                st.write(f"**Contrato:** {d.get('contrato_id', 'N/A')}")
                st.write(f"**✅ Parcelas Pagas:** {p_parc}")
                st.write(f"**⏳ Parcelas Restantes:** {r_parc}")
                st.write(f"**📊 Total do Contrato:** {t_parc}")
                if t_parc > 0:
                    st.progress(min(1.0, p_parc / t_parc))
        else:
            st.warning("Nenhum dado encontrado para este CPF.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        with st.container():
            u = st.text_input("Usuário Corporativo")
            p = st.text_input("Senha", type='password')
            if st.button("ACESSAR PAINEL"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data
