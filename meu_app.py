import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE TELA ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

# CSS Híbrido: Desktop vs Mobile
st.markdown("""<style>
    .main { background: #f4f7f9; }
    /* Cards Estilizados */
    .stMetric { 
        background: white; padding: 20px; border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 6px solid #002D62;
    }
    /* Logo Mobile Adaptive */
    .logo-container { 
        display: flex; align-items: center; justify-content: center;
        background: white; padding: 20px; border-radius: 15px; 
        margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
    }
    .logo-rrb { font-weight: 900; font-size: 30px; color: #002D62; }
    .logo-dot { color: #d90429; }
    
    /* Botões Grandes para Mobile */
    @media (max-width: 640px) {
        .stButton>button { width: 100%; height: 55px; font-size: 18px; border-radius: 12px; }
        .logo-container { margin-top: -30px; border-radius: 0 0 20px 20px; }
    }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="logo-container"><span class="logo-rrb">RRB<span class="logo-dot">.</span>SOLUÇÕES</span></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro de Configuração (Secrets)"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()
def c_h(p, h_t): return h(p) == h_t

# --- NAVEGAÇÃO ---
menu = ["👤 Funcionário (App)", "🏢 Empresa (Gestão)", "⚙️ Admin"]
m = st.sidebar.selectbox("Módulo", menu)

# 1. MÓDULO FUNCIONÁRIO (APP MOBILE)
if m == "👤 Funcionário (App)":
    st.subheader("🔎 Consulta de Transparência")
    cpf_in = st.text_input("Digite seu CPF", placeholder="00000000000")
    cpf = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("CONSULTAR MEU CONSIGNADO"):
        if cpf:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
            if r.data:
                d = r.data[0]
                st.success(f"Olá, {d['nome_funcionario'].split()[0]}!")
                
                # Exibição em cards
                c1, c2 = st.columns([1, 1])
                with c1: st.metric("Desconto em Folha", f"R$ {d['valor_rh']}")
                with c2: st.metric("Valor do Banco", f"R$ {d['valor_banco']}")
                
                if d['diferenca'] == 0:
                    st.info("✅ Status: Valores em conformidade.")
                else:
                    st.error(f"❌ Alerta: Diferença de R$ {abs(d['diferenca'])}")
                    st.warning("Recomendamos entrar em contato com o RH da sua empresa.")
            else:
                st.warning("CPF não localizado para o período atual.")

# 2. MÓDULO EMPRESA (DESKTOP / GESTÃO)
elif m == "🏢 Empresa (Gestão)":
    if 'auth' not in st.session_state: st.session_state.auth = False
    
    if not st.session_state.auth:
        u, p = st.text_input("Login Empresa"), st.text_input("Senha", type='password')
        if st.button("Entrar no Painel"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and c_h(p, q.data[0]['senha']):
                st.session_state.auth, st.session_state.emp_nome = True, q.data[0]['nome_empresa']; st.rerun()
