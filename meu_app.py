import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, date, timedelta

# Tenta carregar bibliotecas externas
try:
    from supabase import create_client
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Erro: Instale 'fpdf' e 'supabase' no seu ambiente.")
    st.stop()

# ============================================================
# 0) CONFIGURAÇÃO E CSS (VISUAL PLATINUM)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Fundo Gradiente Dinâmico */
    .stApp {
        background: radial-gradient(circle at 2% 2%, rgba(0, 45, 98, 0.15) 0%, transparent 25%),
                    radial-gradient(circle at 98% 98%, rgba(74, 144, 226, 0.1) 0%, transparent 25%),
                    #0e1117;
    }

    /* Estilização de Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: 0.3s;
    }
    .metric-card:hover { border-color: #4a90e2; background: rgba(74, 144, 226, 0.05); }

    /* WhatsApp FAB */
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 60px; height: 60px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 28px; box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4);
        z-index: 1000; text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) SEGURANÇA E UTILITÁRIOS
# ============================================================
def get_sb():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

sb = get_sb()
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

def check_plan_status(exp_date):
    if not exp_date: return False
    return datetime.fromisoformat(str(exp_date)).date() >= date.today()

# Gerador de PDF Premium
def gerar_pdf_platinum(d):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(0, 45, 98); pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 20, "RELATORIO DE AUDITORIA PLATINUM", ln=True, align='C')
    pdf.ln(20); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"NOME: {d.get('nome_funcionario')}", ln=True)
    pdf.cell(0, 10, f"CPF: {d.get('cpf')}", ln=True)
    pdf.ln(5)
    pdf.cell(95, 10, f"Valor Total: R$ {d.get('valor_total_emprestimo', 0):,.2f}", 1)
    pdf.cell(95, 10, f"Pagas/Restantes: {d.get('parcelas_pagas')}/{d.get('parcelas_restantes')}", 1, 1)
    pdf.ln(10); pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 10, "Este documento comprova a analise de conformidade realizada pela RRB Solucoes entre os dados bancarios e a folha de pagamento.")
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área de Transparência do Colaborador")
    st.write("Verifique a situação do seu contrato e baixe o demonstrativo oficial.")

    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 Seu CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("📅 Nascimento", value=date(2000,1,1), min_value=date(1900,1,1), max_value=date(2100,12,31))
        tel_in = c3.text_input("📱 Final Tel.", max_chars=4)

    if st.button("📊 ANALISAR MINHA CONFORMIDADE", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        if res.data:
            d = res.data[0]
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d"):
                st.balloons()
                st.markdown(f"### Olá, {d.get('nome_funcionario')}! 👋")
                
                # Interface Visual com Ícones
                m1, m2, m3, m4 = st.columns(4)
                with m1: st.markdown(f"<div class='metric-card'>💰<br><small>Total Empréstimo</small><br><b>R$ {d.get('valor_total_emprestimo',0):,.2f}</b></div>", unsafe_allow_html=True)
                with m2: st.markdown(f"<div class='metric-card'>✅<br><small>Parc. Pagas</small><br><b>{d.get('parcelas_pagas',0)}</b></div>", unsafe_allow_html=True)
                with m3: st.markdown(f"<div class='metric-card'>⏳<br><small>Restantes</small><br><b>{d.get('parcelas_restantes',0)}</b></div>", unsafe_allow_html=True)
                with m4: st.markdown(f"<div class='metric-card'>⚖️<br><small>Diferença</small><br><b>R$ {d.get('diferenca',0):,.2f}</b></div>", unsafe_allow_html=True)
                
                st.markdown("---")
                pdf_data = gerar_pdf_platinum(d)
                st.download_button("📥 BAIXAR DEMONSTRATIVO DE SITUAÇÃO (PDF)", pdf_data, f"Auditoria_{d['cpf']}.pdf", "application/pdf", use_container_width=True)
            else: st.error("Data de nascimento incorreta.")
        else: st.warning("CPF não localizado em nossa base Platinum.")

# ============================================================
# 3) PORTAL DA EMPRESA (ENCORPADO)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel de Gestão Corporativa")
    
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        t_log, t_rec = st.tabs(["🔐 Login Corporativo", "🔑 Recuperar Acesso"])
        with t_log:
            u = st.text_input("CNPJ ou Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("ACESSAR DASHBOARD"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0]['senha']:
                    if check_plan_status(q.data[0].get("data_expiracao")):
                        st.session_state.emp_auth = q.data[0]; st.rerun()
                    else: st.error("❌ Acesso Bloqueado: Plano Expirado. Contate o Admin.")
                else: st.error("Credenciais inválidas.")
        with t_rec:
            st.info("Informe seu CNPJ para receber instruções de recuperação no e-mail cadastrado.")
            st.text_input("CNPJ da Empresa")
            st.button("SOLICITAR RECUPERAÇÃO")

    else:
        emp = st.session_state.emp_auth
        st.sidebar.success(f"Empresa: {emp['nome_empresa']}")
        
        tab_aud, tab_suporte, tab_perfil = st.tabs(["🔍 Auditoria de Funcionários", "🛠️ Suporte & Chamados", "⚙️ Configurações da Conta"])
        
        with tab_aud:
            st.markdown("### 📋 Base de Dados de Auditoria")
            c1, c2 = st.columns([3,1])
            search = c1.text_input("🔎 Pesquisar Funcionário (Nome ou CPF)")
            
            res = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 Baixar Relatório Completo (CSV)", df.to_csv(), "relatorio_geral.csv", use_container_width=True)
            
            st.markdown("---")
            st.markdown("### ❓ FAQ - Dúvidas Frequentes")
            with st.expander("Como interpretar a coluna 'Diferença'?"): st.write("A diferença indica valores cobrados pelo banco que não constam na folha de RH.")
            with st.expander("Qual o prazo de atualização dos dados?"): st.write("Os dados são sincronizados em tempo real com o banco de dados RRB.")

        with tab_suporte:
            st.markdown("### 🎫 Central de Chamados")
            with st.form("chamado"):
                st.selectbox("Tipo de Problema", ["Divergência de Dados", "Erro no Sistema", "Financeiro", "Outros"])
                st.text_area("Descreva detalhadamente sua solicitação")
                if st.form_submit_button("ABRIR CHAMADO"):
                    st.success("Chamado aberto com sucesso! Protocolo: #"+datetime.now().strftime("%H%M%S"))

        with tab_perfil:
            st.markdown("### 🔐 Segurança e Perfil")
            new_u = st.text_input("Novo Usuário", value=emp['login'])
            new_p = st.text_input("Nova Senha", type="password")
            if st.button("ATUALIZAR CREDENCIAIS"):
                sb.table("empresas").update({"login": new_u, "senha": sha256_hex(new_p)}).eq("id", emp['id']).execute()
                st.success("Dados atualizados! Faça login novamente.")
                st.session_state.emp_auth = None; st.rerun()

# ============================================================
# 4) ADMIN MASTER (DETALHADO)
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Central de Controle Master")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets["SENHA_MASTER"]:
        
        t_cad, t_gestao = st.tabs(["➕ Registrar Empresa", "🏢 Gestão de Parceiros"])
        
        with t_cad:
            with st.form("new_emp"):
                st.subheader("Cadastro de Nova Conta")
                c1, c2 = st.columns(2)
                razao = c1.text_input("Razão Social")
                cnpj = c2.text_input("CNPJ / ID Login")
                reps = st.text_area("Representantes (Nome e E-mail - um por linha)")
                
                col1, col2 = st.columns(2)
                plano = col1.selectbox("Plano de Serviço", ["Platinum Enterprise", "Gold", "Standard"])
                meses = col2.number_input("Vigência (Meses)", value=12)
                
                st.markdown("---")
                st.warning("Termos: Ao cadastrar, a empresa autoriza o processamento de dados conforme LGPD.")
                concordo = st.checkbox("Li e aceito os termos de autorização de uso.")
                
                if st.form_submit_button("EFETIVAR CADASTRO"):
                    if concordo:
                        exp = (date.today() + timedelta(days=meses*30)).isoformat()
                        sb.table("empresas").insert({
                            "nome_empresa": razao, "cnpj": cnpj, "login": cnpj,
                            "senha": sha256_hex("123456"), "plano": plano,
                            "data_expiracao": exp, "status": "Ativa", "representantes": reps
                        }).execute()
