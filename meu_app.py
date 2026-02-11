import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime

# --- 1. CONFIGURAÇÃO (Obrigatório ser a primeira linha executada) ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"<div class='logo-container'><span style='font-size: 40px;'>🛡️</span><div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div></div>", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nos Secrets."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    col1, col2 = st.columns(2)
    cpf_in = col1.text_input("CPF (somente números)")
    dt_nasc_in = col2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
    tel_fim_in = st.text_input("Últimos 4 dígitos do seu celular", max_chars=4)
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            # Validação Tripla (CPF + Data + Telefone)
            check_dt = (str(dt_nasc_in) == str(d.get("data_nascimento", "")))
            check_tl = str(d.get("telefone", "")).endswith(tel_fim_in)
            
            if check_dt and check_tl:
                st.success(f"Bem-vindo, {d['nome_funcionario']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                m2.metric("Banco", d.get('banco_nome', 'N/A'))
                stt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                m3.metric("Status", stt)
                with st.expander("📊 Detalhamento"):
                    st.write(f"**ID Contrato:** {d.get('contrato_id', 'N/A')}")
                    p_pg, p_tt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                    st.write(f"**Parcelas:** {p_pg} de {p_tt}")
                    if p_tt > 0: st.progress(min(p_pg/p_tt, 1.0))
            else:
                st.error("Dados de validação incorretos (Data ou Telefone).")
        else:
            st.warning("CPF não localizado.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u, p = st.text_input("Usuário"), st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.
