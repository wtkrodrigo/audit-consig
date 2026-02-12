import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
from fpdf import FPDF

# ============================================================
# 0) CONFIGURAÇÃO E CSS AVANÇADO (ESTILO PLATINUM)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Glassmorphism Background */
    .stApp {
        background: radial-gradient(circle at 0% 0%, rgba(74, 144, 226, 0.1) 0%, transparent 30%),
                    radial-gradient(circle at 100% 100%, rgba(0, 45, 98, 0.05) 0%, transparent 30%);
    }

    /* Cards Estilizados */
    .rrb-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 16px;
        padding: 25px;
        backdrop-filter: blur(15px);
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* WhatsApp FAB */
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 60px; height: 60px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 28px; box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4);
        z-index: 1000; text-decoration: none; transition: 0.3s;
    }
    .wpp-fab:hover { transform: scale(1.1); }

    .footer-box {
        text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.7;
        border-top: 1px solid rgba(128,128,128,0.15); margin-top: 50px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) UTILITÁRIOS, SEGURANÇA E PDF
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

@st.cache_resource
def get_sb(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb = get_sb()

def gerar_pdf_platinum(d):
    pdf = FPDF()
    pdf.add_page()
    # Design do Cabeçalho
    pdf.set_fill_color(0, 45, 98)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 25, "RELATORIO DE AUDITORIA PLATINUM", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"DADOS DO COLABORADOR", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Nome: {d.get('nome_funcionario')}", ln=True)
    pdf.cell(0, 8, f"CPF: {d.get('cpf')}", ln=True)
    pdf.cell(0, 8, f"Empresa: {d.get('nome_empresa')}", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "DETALHES DO EMPRESTIMO", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Valor Total: R$ {d.get('valor_total_emprestimo', 0):,.2f}", border=1)
    pdf.cell(95, 8, f"Contrato: {d.get('contrato_id')}", border=1, ln=True)
    pdf.cell(95, 8, f"Parcelas Pagas: {d.get('parcelas_pagas', 0)}", border=1)
    pdf.cell(95, 8, f"Parcelas Restantes: {d.get('parcelas_restantes', 0)}", border=1, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "CONFORMIDADE FINANCEIRA", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Valor em Folha (RH): R$ {d.get('valor_rh', 0):,.2f}", ln=True)
    pdf.cell(0, 8, f"Valor no Banco: R$ {d.get('valor_banco', 0):,.2f}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Diferenca Apurada: R$ {d.get('diferenca', 0):,.2f}", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

def check_plan_status(exp_date):
    if not exp_date: return True
    return datetime.fromisoformat(exp_date).date() >= date.today()

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área do Colaborador")
    st.write("Verifique a saúde do seu contrato e baixe seu relatório oficial.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 CPF do Titular", placeholder="000.000.000-00")
        nasc_in = c2.date_input("📅 Nascimento", value=date(2000, 1, 1), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Final Tel.", max_chars=4, placeholder="1234")

    if st.button("📊 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).order("data_processamento", desc=True).limit(1).execute()
        if res.data:
            d = res.data[0]
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d") and digits_only(d.get("telefone")).endswith(tel_in):
                st.balloons()
                st.success(f"Autenticação Confirmada: {d.get('nome_funcionario')}")
                
                # KPIs Platinum
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("💰 Valor Empréstimo", f"R$ {d.get('valor_total_emprestimo', 0):,.2f}")
                k2.metric("✅ Parc. Pagas", f"{d.get('parcelas_pagas', 0)}")
                k3.metric("⏳ Restantes", f"{d.get('parcelas_restantes', 0)}")
                diff = float(d.get('diferenca', 0))
                k4.metric("⚖️ Diferença Folha", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")

                with st.expander("📄 Detalhes do Contrato e Download"):
                    st.write(f"**Instituição:** {d.get('banco_nome')} | **ID Contrato:** {d.get('contrato_id')}")
                    pdf_data = gerar_pdf_platinum(d)
                    st.download_button("📥 BAIXAR RELATÓRIO DE AUDITORIA (PDF)", pdf_data, f"Auditoria_{d.get('cpf')}.pdf", "application/pdf", use_container_width=True)
            else: st.error("Dados de validação não conferem.")
        else: st.warning("CPF não localizado na base.")

# ============================================================
# 3) PORTAL DA EMPRESA
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        tab_log, tab_reset = st.tabs(["🔐 Login Platinum", "🔑 Recuperar Acesso"])
        with tab_log:
            u = st.text_input("Usuário (CNPJ)")
            p = st.text_input("Senha Corporativa", type="password")
            if st.button("ACESSAR SISTEMA"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    if not check_plan_status(q.data[0].get("data_expiracao")):
                        st.error("Plano Expirado.")
                    else:
                        st.session_state.emp_auth = q.data[0]
                        st.rerun()
                else: st.error("Credenciais inválidas.")
    else:
        emp = st.session_state.emp_auth
        st.sidebar.info(f"Conectado como: {emp['nome_empresa']}")
        if st.sidebar.button("Logoff"): st.session_state.emp_auth = None; st.rerun()

        tab_dash, tab_servicos, tab_conta = st.tabs(["📊 Dashboard Auditoria", "🛠️ Serviços e Suporte", "⚙️ Configurações"])

        with tab_dash:
            st.markdown("### 🔍 Gestão de Auditoria")
            search = st.text_input("Filtrar por nome ou CPF")
            res_aud = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            df = pd.DataFrame(res_aud.data)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 Exportar Base Completa (CSV)", df.to_csv(), "relatorio_empresa.csv")
            else: st.info("Nenhum dado disponível.")

        with tab_servicos:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🎫 Chamados Técnicos")
                st.text_input("Assunto")
                st.text_area("Descreva a divergência")
                st.button("ABRIR CHAMADO")
            with c2:
                st.markdown("### 📚 Base de Conhecimento")
                with st.expander("Manuais de Integração"): st.write("Documentos para RH...")

        with tab_conta:
            st.markdown("### 🔐 Segurança da Conta")
            new_u = st.text_input("Login", value=emp['login'])
            new_p = st.text_input("Alterar Senha", type="password")
            if st.button("SALVAR ALTERAÇÕES"):
                sb.table("empresas").update({"login": new_u, "senha": sha256_hex(new_p)}).eq("id", emp['id']).execute()
                st.success("Dados atualizados!")

# ============================================================
# 4) ADMIN MASTER
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Master Platinum Control")
    master_key = st.sidebar.text_input("Chave Mestre de Segurança", type="password")
    
    if master_key == st.secrets["SENHA_MASTER"]:
        t1, t2, t3 = st.tabs(["➕ Nova Empresa", "🏢 Gerenciar Ativos", "📈 Relatórios Globais"])
        
        with t1:
            with st.form("admin_new_emp"):
                st.markdown("### Cadastro de Novos Parceiros")
                col_a, col_b = st.columns(2)
                razao = col_a.text_input("Razão Social")
                cnpj = col_b.text_input("CNPJ (Login)")
                reps = st.text_area("Representantes e Contatos")
                plan = st.selectbox("Nível do Plano", ["Enterprise Platinum", "Standard", "Premium"])
                dur = st.number
