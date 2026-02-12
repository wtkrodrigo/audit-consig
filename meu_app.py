import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
from fpdf import FPDF # Importante para o PDF

# ============================================================
# 0) CONFIGURAÇÃO E CSS AVANÇADO
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp {
        background: radial-gradient(circle at 0% 0%, rgba(74, 144, 226, 0.1) 0%, transparent 30%),
                    radial-gradient(circle at 100% 100%, rgba(0, 45, 98, 0.05) 0%, transparent 30%);
    }
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 55px; height: 55px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; box-shadow: 0 8px 24px rgba(37, 211, 102, 0.3);
        z-index: 1000; text-decoration: none;
    }
    .footer-box {
        text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.6;
        border-top: 1px solid rgba(128,128,128,0.1); margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) UTILITÁRIOS, SEGURANÇA E GERADOR DE PDF
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

@st.cache_resource
def get_sb(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb = get_sb()

def gerar_pdf_colaborador(dados):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Auditoria de Emprestimo", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # Dados do Colaborador
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Dados do Colaborador", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, f"Nome: {dados.get('nome_funcionario')}", ln=True)
    pdf.cell(100, 8, f"CPF: {dados.get('cpf')}", ln=True)
    pdf.cell(100, 8, f"Empresa: {dados.get('nome_empresa')}", ln=True)
    pdf.ln(5)
    
    # Detalhes do Contrato
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Detalhes do Emprestimo e Conformidade", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, f"Banco: {dados.get('banco_nome')}", ln=False)
    pdf.cell(100, 8, f"Contrato: {dados.get('contrato_id')}", ln=True)
    pdf.cell(100, 8, f"Valor Total Emprestimo: R$ {dados.get('valor_total_emprestimo', 0):,.2f}", ln=True)
    pdf.cell(100, 8, f"Parcelas Pagas: {dados.get('parcelas_pagas', 0)}", ln=False)
    pdf.cell(100, 8, f"Parcelas Restantes: {dados.get('parcelas_restantes', 0)}", ln=True)
    pdf.ln(5)
    
    # Financeiro
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Analise de Folha vs Banco", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(100, 8, f"Valor em Folha (RH): R$ {dados.get('valor_rh', 0):,.2f}", ln=True)
    pdf.cell(100, 8, f"Valor no Banco: R$ {dados.get('valor_banco', 0):,.2f}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 8, f"Diferenca: R$ {dados.get('diferenca', 0):,.2f}", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

def render_footer():
    st.markdown(f"""<div class="footer-box">© {date.today().year} RRB Solucoes | Protecao de Dados LGPD</div>""", unsafe_allow_html=True)

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área do Colaborador")
    st.write("Consulte seu contrato e parcelas em aberto.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 Digite seu CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("📅 Data de Nascimento", value=date(2000, 1, 1), min_value=date(1900, 1, 1), max_value=date(2100, 12, 31), format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Fim do Telefone", max_chars=4, placeholder="1234")

    if st.button("📊 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).order("data_processamento", desc=True).limit(1).execute()
        
        if res.data:
            d = res.data[0]
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d") and digits_only(d.get("telefone")).endswith(tel_in):
                st.balloons()
                st.markdown(f"### Olá, {d.get('nome_funcionario')}!")
                
                # --- NOVOS KPIS DE EMPRÉSTIMO ---
                k1, k2, k3, k4 = st.columns(4)
                v_total = float(d.get('valor_total_emprestimo', 0))
                p_pagas = int(d.get('parcelas_pagas', 0))
                p_falta = int(d.get('parcelas_restantes', 0))
                
                k1.metric("💰 Valor Total", f"R$ {v_total:,.2f}")
                k2.metric("✅ Pagas", f"{p_pagas} parcs")
                k3.metric("⏳ Restantes", f"{p_falta} parcs")
                k4.metric("📊 Status", "CONFORME" if abs(float(d.get('diferenca', 0))) < 0.05 else "DIVERGENTE")

                st.markdown("---")
                
                # Detalhes Financeiros
                col_fin1, col_fin2 = st.columns(2)
                with col_fin1:
                    st.info(f"**Banco:** {d.get('banco_nome')} | **Contrato:** {d.get('contrato_id')}")
                with col_fin2:
                    # GERAÇÃO DO PDF AO CLICAR
                    pdf_bytes = gerar_pdf_colaborador(d)
                    st.download_button(
                        label="📥 BAIXAR COMPROVANTE OFICIAL (PDF)",
                        data=pdf_bytes,
                        file_name=f"Auditoria_{d.get('cpf')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else: st.error("Validação falhou. Verifique os dados informados.")
        else: st.warning("CPF não localizado.")

# ============================================================
# 3) PORTAL DA EMPRESA E ADMIN (MANTIDOS)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None
    if not st.session_state.emp_auth:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and sha256_hex(p) == q.data[0].get("senha"):
                st.session_state.emp_auth = q.data[0]; st.rerun()
            else: st.error("Erro de login")
    else:
        emp = st.session_state.emp_auth
        st.write(f"Empresa: {emp['nome_empresa']}")
        res_aud = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
        df = pd.DataFrame(res_aud.data)
        st.dataframe(df)
        if st.sidebar.button("Sair"): st.session_state.emp_auth = None; st.rerun()

def portal_admin():
    st.markdown("# ⚙️ Master Control")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets["SENHA_MASTER"]:
        st.write("Bem-vindo, Administrador.")
        # Gestão de empresas aqui...

# ============================================================
# NAVEGAÇÃO PRINCIPAL
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
if menu == "👤 Funcionário": portal_funcionario()
elif menu == "🏢 Empresa": portal_empresa()
else: portal_admin()

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
render_footer()
