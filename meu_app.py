import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO (O ESCUDO E LOGO) ---
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
    st.error("Erro de conexão com o banco de dados."); st.stop()

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
            st.success(f"Bem-vindo, {d['nome_funcionario']}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
            c3.metric("Status", status)
            
            # Cálculo de parcelas para o funcionário
            total_parc = int(d.get('parcelas_total', 0))
            pagas_parc = int(d.get('parcelas_pagas', 0))
            restantes_parc = max(0, total_parc - pagas_parc)
            
            with st.expander("📊 Detalhamento do Empréstimo"):
                col_a, col_b = st.columns(2)
                col_a.write(f"**Valor do Empréstimo:** R
