import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io  # Necessário para processamento de arquivos

# ============================================================
# 0) SEGURANÇA E CONFIGURAÇÃO
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

# Função para conectar ao Supabase com tratamento de erro
@st.cache_resource
def get_sb():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("⚠️ Erro de Configuração: Verifique os Secrets no Streamlit/GitHub.")
        return None

sb = get_sb()

# Funções utilitárias
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

def check_plan_status(exp_date):
    if not exp_date: return False
    try:
        if isinstance(exp_date, str):
            exp_date = datetime.strptime(exp_date[:10], "%Y-%m-%d").date()
        return exp_date >= date.today()
    except:
        return False

# ============================================================
# 1) ESTILO CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stMetric { background: rgba(74, 144, 226, 0.05); padding: 15px; border-radius: 15px; border-left: 5px solid #4A90E2; }
    .wpp-fab { position: fixed; bottom: 30px; right: 30px; background: #25D366; color: white !important;
               width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; 
               justify-content: center; font-size: 30px; box-shadow: 0 10px 25px rgba(37,211,102,0.4); 
               z-index: 1000; text-decoration: none; transition: 0.3s; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO
# ============================================================
def portal_funcionario():
    st.markdown("# 👤 Portal do Colaborador")
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🆔 CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("🎂 Data de Nascimento", format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Final do Telefone", max_chars=4)

    if st.button("🚀 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        if not sb: return
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        if res.data:
            d = res.data[0]
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d"):
                st.success(f"Olá, {d.get('nome_funcionario')}!")
                k1, k2, k3, k4 = st.columns(4)
                v_rh, v_bnc = float(d.get('valor_rh', 0)), float(d.get('valor_banco', 0))
                diff = v_rh - v_bnc
                k1.metric("📄 Valor em Folha", f"R$ {v_rh:,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {v_bnc:,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                k4.metric("📈 Status", "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE")
                
                csv = pd.DataFrame([d]).to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Relatório (CSV)", csv, "auditoria.csv", "text/csv")
            else: st.error("❌ Data de nascimento incorreta.")
        else: st.warning("⚠️ Registro não encontrado.")

# ============================================================
# 3) PORTAL DA EMPRESA
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        t1, t2 = st.tabs(["🔐 Login", "🔑 Esqueci Senha"])
        with t1:
            u, p = st.text_input("CNPJ (Login)"), st.text_input("Senha", type="password")
            if st.button("ACESSAR"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    if check_plan_status(q.data[0].get("data_expiracao")):
                        st.session_state.emp_auth = q.data[0]
                        st.rerun()
                    else: st.error("🚨 Plano Expirado.")
                else: st.error("Acesso negado.")
    else:
        emp = st.session_state.emp_auth
        st.sidebar.write(f"Empresa: {emp['nome_empresa']}")
        tabs = st.tabs(["📊 Dashboard", "🔍 Pesquisa", "📥 Exportar", "🎫 Suporte", "⚙️ Conta"])
        
        res = sb.table("resultados_auditoria").eq("nome_empresa", emp['nome_empresa']).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

        with tabs[0]:
            if not df.empty:
                c1, c2 = st.columns(2)
                c1.metric("Total Funcionários", len(df))
                st.bar_chart(df.set_index('nome_funcionario')[['valor_rh', 'valor_banco']])
            else: st.info("Sem dados para exibir.")
        
        with tabs[4]:
            if st.button("Sair / Logoff"):
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 4) ADMIN MASTER
# ============================================================
def portal_admin():
    st.markdown("# 🛡️ Master Control")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets.get("SENHA_MASTER", "admin123"):
        t1, t2, t3 = st.tabs(["🏢 Empresas", "➕ Novo Contrato", "📤 Upload CSV"])
        
        with t3:
            st.subheader("Sincronização de Dados")
            emps = sb.table("empresas").select("nome_empresa").execute()
            lista = [e['nome_empresa'] for e in emps.data]
            destino = st.selectbox("Empresa Destino", lista)
            file = st.file_uploader("Arquivo CSV", type="csv")
            if file and st.button("🔥 Iniciar Sincronização"):
                df_up = pd.read_csv(file)
                regs = []
                for _, r in df_up.iterrows():
                    v1, v2 = float(r.get('valor_rh',0)), float(r.get('valor_banco',0))
                    regs.append({
                        "nome_funcionario": r.get('nome'), "cpf": digits_only(str(r.get('cpf'))),
                        "data_nascimento": str(r.get('data_nascimento')), "valor_rh": v1,
                        "valor_banco": v2, "diferenca": v1-v2, "nome_empresa": destino
                    })
                sb.table("resultados_auditoria").insert(regs).execute()
                st.success("Dados Sincronizados!")
    else: st.warning("Acesso restrito.")

# ============================================================
# MAIN
# ============================================================
nav = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])
if nav == "👤 Funcionário": portal_funcionario()
elif nav == "🏢 Empresa": portal_empresa()
else: portal_admin()

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
