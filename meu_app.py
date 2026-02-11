import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

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
    s_url = st.secrets["SUPABASE_URL"]
    s_key = st.secrets["SUPABASE_KEY"]
    sb = create_client(s_url, s_key)
except Exception as e:
    st.error("Erro crítico: Verifique os Secrets do Supabase.")
    st.stop()

def h(p):
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("Para sua segurança, valide seus dados abaixo.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc = c2.date_input("Data de Nascimento", min_value=datetime(1940, 1, 1), format="DD/MM/YYYY")
        tel_fim = st.text_input("Últimos 4 dígitos do telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
        
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                # Validação de segurança
                check_dt = str(dt_nasc) == str(d.get("data_nascimento", ""))
                check_tel = str(d.get("telefone", "")).endswith(tel_fim)
                
                if check_dt and check_tel:
                    st.success(f"Bem-vindo, {d['nome_funcionario']}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Banco", d.get('banco_nome', 'N/A'))
                    status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status", status)
                    
                    with st.expander("Detalhamento do Contrato"):
                        p_pagas = int(d.get("parcelas_pagas", 0))
                        p_total = int(d.get("parcelas_total", 0))
                        st.write(f"**Contrato:** {d.get('contrato_id', 'N/A')}")
                        st.write(f"**Parcelas Pagas:** {p_pagas} de {p_total}")
                        if p_total > 0:
                            prog = min(p_pagas / p_total, 1.0)
                            st.progress(prog, text=f"Progresso: {int(prog*100)}%")
                else:
                    st.error("Dados de validação incorretos (Data ou Telefone).")
            else:
                st.warning("Nenhum registro encontrado para este CPF.")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if "at" not in st.session_state:
        st.session_state.at = False
    
    if not st.session_state.at:
        u_corp = st.text_input("Usuário Corporativo")
        p_corp = st.text_input("Senha", type="password")
        if st.button("ACESSAR PAINEL"):
            q = sb.table("empresas").select("*").eq("login", u_corp).execute()
            if q.data and h(p_corp) == q.data[0]["senha"]:
