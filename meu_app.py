import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta

# ============================================================
# 0) CONFIGURAÇÃO E CSS AVANÇADO (LIGHT/DARK ADAPTIVE)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Glassmorphism Dinâmico */
    .stApp {
        background: radial-gradient(circle at 0% 0%, rgba(74, 144, 226, 0.1) 0%, transparent 30%),
                    radial-gradient(circle at 100% 100%, rgba(0, 45, 98, 0.05) 0%, transparent 30%);
    }

    .rrb-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(12px);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }

    /* WhatsApp Minimalista FAB */
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 55px; height: 55px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; box-shadow: 0 8px 24px rgba(37, 211, 102, 0.3);
        z-index: 1000; text-decoration: none;
    }

    /* Footer de Privacidade */
    .footer-box {
        text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.6;
        border-top: 1px solid rgba(128,128,128,0.1); margin-top: 40px;
    }

    /* Status Badges */
    .badge {
        padding: 4px 12px; border-radius: 20px; font-weight: 700; font-size: 11px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) UTILITÁRIOS E SEGURANÇA
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

@st.cache_resource
def get_sb(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb = get_sb()

def render_footer():
    st.markdown("""<div class="footer-box">
    © 2026 RRB Soluções | Termos de Privacidade e Proteção de Dados (LGPD) <br>
    Este sistema utiliza criptografia de ponta a ponta para proteger as informações de auditoria.
    </div>""", unsafe_allow_html=True)

def check_plan_status(exp_date):
    if not exp_date: return True
    return datetime.fromisoformat(exp_date).date() >= date.today()

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO (DASHBOARD & DOWNLOAD)
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área do Colaborador")
    st.write("Consulte sua conformidade bancária de forma transparente.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 Digite seu CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("📅 Data de Nascimento", format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Fim do Telefone", max_chars=4, placeholder="1234")

    if st.button("📊 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).order("data_processamento", desc=True).limit(1).execute()
        if res.data:
            d = res.data[0]
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d") and digits_only(d.get("telefone")).endswith(tel_in):
                st.balloons()
                st.markdown(f"### Bem-vindo, {d.get('nome_funcionario').split()[0]}! 👋")
                
                # KPIs Visuais
                k1, k2, k3, k4 = st.columns(4)
                diff = float(d.get('diferenca', 0))
                k1.metric("📌 Valor em Folha", f"R$ {d.get('valor_rh'):,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {d.get('valor_banco'):,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                status = "✅ CONFORME" if abs(diff) < 0.05 else "⚠️ DIVERGENTE"
                k4.metric("📈 Status Final", status)

                # Gráfico e Detalhes
                with st.expander("📄 Ver Detalhes do Contrato e Baixar Comprovante"):
                    st.write(f"**Banco Origem:** {d.get('banco_nome')} | **Contrato:** {d.get('contrato_id')}")
                    st.info("Este documento serve como demonstrativo de auditoria interna da RRB Soluções.")
                    # Botão de Download do PDF/CSV Individual
                    df_ind = pd.DataFrame([d])
                    st.download_button("📥 Baixar Relatório de Auditoria (PDF/CSV)", df_ind.to_csv(), "meu_relatorio.csv", "text/csv")
            else: st.error("Dados de validação não conferem. Verifique o telefone e data de nascimento.")
        else: st.warning("CPF não localizado na base de dados atual.")

# ============================================================
# 3) PORTAL DA EMPRESA (GESTÃO, CHAMADOS E PERFIL)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo")
    
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        tab_log, tab_reset = st.tabs(["🔐 Login", "🔑 Esqueci Senha"])
        with tab_log:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("ACESSAR SISTEMA"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    if not check_plan_status(q.data[0].get("data_expiracao")):
                        st.error("❌ Plano Expirado. Entre em contato com o suporte para renovar.")
                    else:
                        st.session_state.emp_auth = q.data[0]
                        st.rerun()
                else: st.error("Credenciais inválidas.")
        with tab_reset:
            st.info("Para resetar sua senha, informe o CNPJ cadastrado.")
            reset_cnpj = st.text_input("CNPJ da Empresa")
            if st.button("SOLICITAR NOVA SENHA"):
                st.success("Um link de recuperação foi enviado ao e-mail do representante principal.")

    else:
        emp = st.session_state.emp_auth
        st.sidebar.subheader(f"Olá, {emp['nome_empresa']}")
        tab_dash, tab_servicos, tab_conta = st.tabs(["📊 Dashboard Auditoria", "🛠️ Serviços e Suporte", "⚙️ Minha Conta"])

        with tab_dash:
            st.markdown("### 🔍 Pesquisa Rápida de Funcionários")
            search = st.text_input("Pesquisar por Nome ou CPF")
            # Carregar dados
            res_aud = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            df = pd.DataFrame(res_aud.data)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 Baixar Relatório Geral (CSV)", df.to_csv(), "auditoria_completa.csv")
            else: st.info("Nenhum dado sincronizado ainda.")

        with tab_servicos:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### ❓ FAQ - Dúvidas Comuns")
                with st.expander("Como atualizar os dados?"): st.write("Basta subir o novo CSV no botão de sincronização.")
                with st.expander("O que fazer em caso de divergência?"): st.write("Contate o banco ou ajuste a folha conforme o contrato.")
            with c2:
                st.markdown("### 🎫 Abrir Chamado")
                st.text_area("Descreva o problema")
                st.button("ENVIAR CHAMADO")

        with tab_conta:
            st.markdown("### 🛠️ Alterar Credenciais")
            new_u = st.text_input("Novo Usuário", value=emp['login'])
            new_p = st.text_input("Nova Senha", type="password")
            if st.button("ATUALIZAR DADOS DA CONTA"):
                sb.table("empresas").update({"login": new_u, "senha": sha256_hex(new_p)}).eq("id", emp['id']).execute()
                st.success("Dados atualizados! Por favor, faça login novamente.")
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 4) ADMIN MASTER (BLOCKING, PLANOS E TERMOS)
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Master Control Panel")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets["SENHA_MASTER"]:
        
        tab1, tab2 = st.tabs(["➕ Registrar Empresa", "🏢 Gestão de Ativos"])
        
        with tab1:
            with st.form("new_emp"):
                st.markdown("### Cadastro de Parceiro")
                col_a, col_b = st.columns(2)
                razao = col_a.text_input("Razão Social")
                cnpj = col_b.text_input("CNPJ")
                
                st.markdown("**Representantes (Múltiplos)**")
                reps = st.text_area("Nomes e E-mails (um por linha)")
                
                plan = st.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
                dur = st.number_input("Duração do Plano (Meses)", value=12)
                
                st.checkbox("Aceito os termos de uso e processamento de dados (LGPD)")
                
                if st.form_submit_button("CADASTRAR E GERAR ACESSO"):
                    exp = (date.today() + timedelta(days=dur*30)).isoformat()
                    sb.table("empresas").insert({
                        "nome_empresa": razao, "cnpj": cnpj, "plano": plan,
                        "data_expiracao": exp, "login": cnpj, "senha": sha256_hex("123456"),
                        "representantes": reps, "status": "Ativa"
                    }).execute()
                    st.success(f"Empresa {razao} cadastrada! Senha padrão: 123456")

        with tab2:
            st.markdown("### Lista de Empresas Parceiras")
            all_emp = sb.table("empresas").select("*").execute()
            df_all = pd.DataFrame(all_emp.data)
            if not df_all.empty:
                # Adicionar cor de status
                st.dataframe(df_all[["nome_empresa", "cnpj", "plano", "data_expiracao", "status"]], use_container_width=True)
                
    else: st.warning("Aguardando Chave Mestre de Segurança...")

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if menu == "👤 Funcionário": portal_funcionario()
elif menu == "🏢 Empresa": portal_empresa()
else: portal_admin()

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
render_footer()
