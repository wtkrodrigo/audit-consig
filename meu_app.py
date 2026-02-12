import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, date, timedelta

# 1. Configuração de Página (Primeira linha sempre)
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

# 2. Importações e Conexão Segura
try:
    from supabase import create_client
    from fpdf import FPDF
except ImportError:
    st.error("🚨 Erro: Verifique seu requirements.txt (fpdf e supabase são necessários).")
    st.stop()

def get_sb():
    try:
        if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
            return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        return None
    except: return None

sb = get_sb()

# --- Funções Utilitárias ---
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

def check_plan_status(exp_date):
    if not exp_date: return False
    try:
        dt = datetime.strptime(str(exp_date)[:10], "%Y-%m-%d").date()
        return dt >= date.today()
    except: return False

# --- Gerador de PDF Platinum ---
def gerar_pdf_platinum(d):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(0, 45, 98); pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 20, "RRB AUDITORIA - DEMONSTRATIVO OFICIAL", ln=True, align='C')
    pdf.ln(20); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"NOME: {str(d.get('nome_funcionario')).upper()}", ln=True)
    pdf.cell(0, 10, f"CPF: {d.get('cpf')}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(95, 10, "VALOR DO EMPRESTIMO", 1, 0, 'L', True)
    pdf.cell(95, 10, f"R$ {d.get('valor_total_emprestimo', 0):,.2f}", 1, 1)
    pdf.cell(95, 10, "PARCELAS PAGAS", 1, 0, 'L', True)
    pdf.cell(95, 10, f"{d.get('parcelas_pagas', 0)}", 1, 1)
    pdf.cell(95, 10, "PARCELAS RESTANTES", 1, 0, 'L', True)
    pdf.cell(95, 10, f"{d.get('parcelas_restantes', 0)}", 1, 1)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- CSS ENTERPRISE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: #0e1117; }
    .metric-card {
        background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(74, 144, 226, 0.3);
        border-radius: 15px; padding: 20px; text-align: center; transition: 0.3s;
    }
    .metric-card:hover { border-color: #4a90e2; background: rgba(74, 144, 226, 0.1); }
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px; background: #25D366; color: white !important;
        width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; 
        justify-content: center; font-size: 28px; z-index: 1000; text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Navegação RRB Platinum", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# ==========================================
# ABA FUNCIONÁRIO
# ==========================================
if menu == "👤 Funcionário":
    st.markdown("# 🛡️ Portal do Colaborador")
    st.write("Consulte detalhes do seu empréstimo e baixe o demonstrativo.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("📅 Nascimento", value=date(2000,1,1), min_value=date(1900,1,1))
        tel_in = c3.text_input("📱 Final Tel.", max_chars=4)

    if st.button("📊 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        if sb:
            res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
            if res.data:
                d = res.data[0]
                if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d"):
                    st.balloons()
                    st.success(f"Olá, {d.get('nome_funcionario')}! Seus dados foram localizados.")
                    
                    # KPIs Visuais
                    m1, m2, m3, m4 = st.columns(4)
                    with m1: st.markdown(f"<div class='metric-card'>💰<br><small>Total Empréstimo</small><br><b>R$ {d.get('valor_total_emprestimo',0):,.2f}</b></div>", unsafe_allow_html=True)
                    with m2: st.markdown(f"<div class='metric-card'>✅<br><small>Pagas</small><br><b>{d.get('parcelas_pagas',0)}</b></div>", unsafe_allow_html=True)
                    with m3: st.markdown(f"<div class='metric-card'>⏳<br><small>Restantes</small><br><b>{d.get('parcelas_restantes',0)}</b></div>", unsafe_allow_html=True)
                    with m4: st.markdown(f"<div class='metric-card'>⚖️<br><small>Diferença</small><br><b>R$ {d.get('diferenca',0):,.2f}</b></div>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    pdf_bytes = gerar_pdf_platinum(d)
                    st.download_button("📥 BAIXAR DEMONSTRATIVO DE SITUAÇÃO (PDF)", pdf_bytes, "Relatorio_Auditoria.pdf", "application/pdf", use_container_width=True)
                else: st.error("Data de nascimento incorreta.")
            else: st.warning("CPF não encontrado.")
        else: st.error("Banco de dados offline.")

# ==========================================
# ABA EMPRESA
# ==========================================
elif menu == "🏢 Empresa":
    st.markdown("# 🏢 Painel Corporativo")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        t_log, t_rec = st.tabs(["🔐 Login Platinum", "🔑 Esqueci a Senha"])
        with t_log:
            u = st.text_input("Usuário (CNPJ)")
            p = st.text_input("Senha", type="password")
            if st.button("ENTRAR NO PAINEL"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0]['senha']:
                    if check_plan_status(q.data[0].get("data_expiracao")):
                        st.session_state.emp_auth = q.data[0]; st.rerun()
                    else: st.error("❌ Plano Expirado. Contate o Admin.")
                else: st.error("Credenciais inválidas.")
        with t_rec:
            st.info("Para recuperar o acesso, solicite o reset de senha ao administrador do sistema.")
    else:
        emp = st.session_state.emp_auth
        st.sidebar.info(f"Empresa: {emp['nome_empresa']}")
        if st.sidebar.button("Logoff"): st.session_state.emp_auth = None; st.rerun()

        tab1, tab2, tab3, tab4 = st.tabs(["🔍 Pesquisa e Relatórios", "🎫 Chamados", "❓ FAQ", "⚙️ Perfil"])
        
        with tab1:
            st.markdown("### Pesquisar Colaborador")
            res = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 BAIXAR RELATÓRIO COMPLETO (CSV)", df.to_csv(), "relatorio_geral.csv", use_container_width=True)
        
        with tab2:
            st.markdown("### Abrir Chamado de Suporte")
            st.text_input("Assunto")
            st.text_area("Descreva a divergência ou dúvida")
            st.button("ENVIAR CHAMADO")

        with tab3:
            st.markdown("### Dúvidas Frequentes (FAQ)")
            with st.expander("O que é o Status Conforme?"): st.write("Significa que os valores batem 100%.")
            with st.expander("Como solicitar novas auditorias?"): st.write("Entre em contacto com o suporte via WhatsApp.")

        with tab4:
            st.markdown("### Alterar Credenciais")
            new_u = st.text_input("Novo Usuário", value=emp['login'])
            new_p = st.text_input("Nova Senha", type="password")
            if st.button("SALVAR ALTERAÇÕES"):
                sb.table("empresas").update({"login": new_u, "senha
