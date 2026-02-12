import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, date, timedelta

# Tenta carregar bibliotecas externas com segurança
try:
    from supabase import create_client
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Erro de dependências. Verifique se 'fpdf' e 'supabase' estão no seu requirements.txt")
    st.stop()

# ============================================================
# 0) CONFIGURAÇÃO INICIAL (OBRIGATÓRIO SER A PRIMEIRA LINHA)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

# ============================================================
# 1) CONEXÃO E SEGURANÇA (SUPABASE & SECRETS)
# ============================================================
def get_sb():
    try:
        # Verifica se os segredos existem antes de tentar conectar
        if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
            return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        return None
    except:
        return None

sb = get_sb()

def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

# ============================================================
# 2) GERADOR DE RELATÓRIO PDF PLATINUM
# ============================================================
def gerar_pdf_platinum(d):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho Estilizado
    pdf.set_fill_color(0, 45, 98)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 20, "RRB SOLUCOES - AUDITORIA PLATINUM", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    
    # Seção: Identificação
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. IDENTIFICACAO DO COLABORADOR", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Nome: {d.get('nome_funcionario', 'N/A')}", ln=True)
    pdf.cell(0, 8, f"CPF: {d.get('cpf', 'N/A')}", ln=True)
    pdf.cell(0, 8, f"Empresa: {d.get('nome_empresa', 'N/A')}", ln=True)
    
    pdf.ln(5)
    
    # Seção: Detalhes do Empréstimo (Ajuste solicitado)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. DETALHES DO EMPRESTIMO", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 10, f"Valor Total: R$ {d.get('valor_total_emprestimo', 0):,.2f}", border=1)
    pdf.cell(95, 10, f"Contrato: {d.get('contrato_id', 'N/A')}", border=1, ln=True)
    pdf.cell(95, 10, f"Parcelas Pagas: {d.get('parcelas_pagas', 0)}", border=1)
    pdf.cell(95, 10, f"Parcelas Restantes: {d.get('parcelas_restantes', 0)}", border=1, ln=True)
    
    pdf.ln(5)
    
    # Seção: Auditoria
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "3. PARECER DE CONFORMIDADE", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Valor em Folha: R$ {d.get('valor_rh', 0):,.2f}", ln=True)
    pdf.cell(0, 8, f"Valor no Banco: R$ {d.get('valor_banco', 0):,.2f}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Diferenca: R$ {d.get('diferenca', 0):,.2f}", ln=True)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# ============================================================
# 3) INTERFACE CSS E DESIGN
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background: radial-gradient(circle at 0% 0%, rgba(74, 144, 226, 0.05) 0%, transparent 30%); }
    .wpp-fab { position: fixed; bottom: 30px; right: 30px; background: #25D366; color: white !important;
               width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; 
               justify-content: center; font-size: 28px; z-index: 1000; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 4) NAVEGAÇÃO PRINCIPAL
# ============================================================
menu = st.sidebar.radio("Navegação Platinum", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- ABA FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    st.markdown("# 🛡️ Portal do Colaborador")
    st.write("Consulte sua auditoria bancária com transparência.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 Digite seu CPF")
        nasc_in = c2.date_input("📅 Nascimento", value=date(2000, 1, 1), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))
        tel_in = c3.text_input("📱 Final Telefone", max_chars=4)

    if st.button("📊 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        if not sb:
            st.error("Conexão com banco de dados não configurada corretamente nos Secrets.")
        else:
            res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
            if res.data:
                d = res.data[0]
                if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d"):
                    st.success(f"Bem-vindo, {d.get('nome_funcionario')}!")
                    
                    # KPIs de Empréstimo
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("💰 Valor Total", f"R$ {d.get('valor_total_emprestimo', 0):,.2f}")
                    k2.metric("✅ Pagas", d.get("parcelas_pagas", 0))
                    k3.metric("⏳ Restantes", d.get("parcelas_restantes", 0))
                    k4.metric("⚖️ Diferença", f"R$ {d.get('diferenca', 0):,.2f}")
                    
                    pdf_bytes = gerar_pdf_platinum(d)
                    st.download_button("📥 BAIXAR RELATÓRIO OFICIAL (PDF)", pdf_bytes, f"Relatorio_{d['cpf']}.pdf", "application/pdf", use_container_width=True)
                else:
                    st.error("Data de nascimento não confere.")
            else:
                st.warning("CPF não localizado.")

# --- ABA EMPRESA ---
elif menu == "🏢 Empresa":
    st.markdown("# 🏢 Painel Corporativo Platinum")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None
    
    if not st.session_state.emp_auth:
        u = st.text_input("CNPJ (Usuário)")
        p = st.text_input("Senha", type="password")
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and sha256_hex(p) == q.data[0]['senha']:
                st.session_state.emp_auth = q.data[0]
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        emp = st.session_state.emp_auth
        st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"emp_auth": None}))
        
        tab1, tab2, tab3 = st.tabs(["📊 Auditoria Geral", "🛠️ Suporte", "⚙️ Minha Conta"])
        with tab1:
            res = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        with tab2:
            st.write("Abrir chamado técnico para suporte RRB.")
            st.text_area("Descreva o problema")
            st.button("Enviar")
        with tab3:
            st.write(f"Empresa: {emp['nome_empresa']}")
            st.write(f"Plano: {emp['plano']}")

# --- ABA ADMIN ---
elif menu == "⚙️ Admin Master":
    st.markdown("# ⚙️ Controle Master")
    m_key = st.sidebar.text_input("Chave Mestre", type="password")
    if m_key == st.secrets.get("SENHA_MASTER"):
        t1, t2 = st.tabs(["🏢 Gerenciar Empresas", "📈 Visão Global"])
        with t1:
            st.write("Lista de empresas parceiras e status de planos.")
            if sb:
                emps = sb.table("empresas").select("*").execute()
                st.table(pd.DataFrame(emps.data)[["nome_empresa", "cnpj", "plano", "status"]])
    else:
        st.info("Insira a Chave Mestre para acessar.")

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
