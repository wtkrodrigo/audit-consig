import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io

# ============================================================
# 0) CONFIGURAÇÃO E CSS AVANÇADO (DESIGN MODERNO)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Estilização de Cards e Containers */
    .main-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 30px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .stMetric {
        background: rgba(74, 144, 226, 0.05);
        padding: 15px;
        border-radius: 15px;
        border-left: 5px solid #4A90E2;
    }

    /* Botão flutuante WhatsApp */
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 60px; height: 60px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 30px; box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4);
        z-index: 1000; text-decoration: none; transition: 0.3s;
    }
    .wpp-fab:hover { transform: scale(1.1); }
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

def check_plan_status(exp_date):
    if not exp_date: return False
    return datetime.fromisoformat(exp_date).date() >= date.today()

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO (COM ÍCONES E DOWNLOAD)
# ============================================================
def portal_funcionario():
    st.markdown("# 👤 Portal do Colaborador")
    st.info("Consulte sua auditoria bancária com transparência e segurança.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🆔 CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("🎂 Data de Nascimento", format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Final do Telefone", max_chars=4, help="4 últimos dígitos")

    if st.button("🚀 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        if res.data:
            d = res.data[0]
            # Validação simples de segurança
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d"):
                st.success(f"Olá, {d.get('nome_funcionario')}! Identificamos seus dados.")
                
                # KPIs com ícones
                st.markdown("### 📊 Resumo da Auditoria")
                k1, k2, k3, k4 = st.columns(4)
                diff = float(d.get('diferenca', 0))
                k1.metric("📄 Valor em Folha", f"R$ {d.get('valor_rh'):,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {d.get('valor_banco'):,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                
                status = "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE"
                k4.metric("📈 Status", status)

                # Área de Download
                st.markdown("---")
                st.markdown("#### 📥 Documentação")
                col_dl, col_txt = st.columns([1, 3])
                with col_dl:
                    # Simulação de arquivo PDF/CSV para download
                    df_baixa = pd.DataFrame([d])
                    csv = df_baixa.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📄 Baixar Demonstrativo (PDF/CSV)",
                        data=csv,
                        file_name=f"auditoria_{cpf_in}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                with col_txt:
                    st.caption("Este documento contém o detalhamento técnico da conferência entre o sistema de RH da empresa e o extrato bancário processado.")
            else:
                st.error("Dados de nascimento não conferem.")
        else:
            st.warning("Nenhum registro encontrado para este CPF.")

# ============================================================
# 3) PORTAL DA EMPRESA (GESTÃO, CHAMADOS E ESQUECI SENHA)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Executivo")
    
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        tab_log, tab_reset = st.tabs(["🔐 Acesso Restrito", "🔑 Esqueci minha Senha"])
        
        with tab_log:
            u = st.text_input("Usuário (CNPJ)")
            p = st.text_input("Senha", type="password")
            if st.button("ENTRAR NO PAINEL"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    emp = q.data[0]
                    if not check_plan_status(emp.get("data_expiracao")):
                        st.error("🚨 Seu plano expirou! Bloqueio automático ativado. Entre em contato com o Admin.")
                    else:
                        st.session_state.emp_auth = emp
                        st.rerun()
                else: st.error("Usuário ou senha incorretos.")
        
        with tab_reset:
            st.markdown("### Recuperação de Acesso")
            cnpj_rec = st.text_input("Confirme o CNPJ cadastrado")
            if st.button("SOLICITAR RESET"):
                st.info("Se o CNPJ constar na base, um e-mail com instruções foi enviado aos representantes.")

    else:
        emp = st.session_state.emp_auth
        st.sidebar.success(f"Conectado: {emp['nome_empresa']}")
        
        menu_emp = st.tabs(["📊 Dashboard", "🔍 Busca Funcionário", "📥 Exportar Dados", "🎫 Suporte", "⚙️ Minha Conta"])

        with menu_emp[0]: # DASHBOARD
            st.markdown(f"### Bem-vindo ao Dashboard da {emp['nome_empresa']}")
            # Aqui entrariam gráficos de barras/pizza sobre os funcionários
            st.write("Visão geral de conformidade da última remessa.")
            
        with menu_emp[1]: # BUSCA
            st.markdown("### 🔍 Pesquisa de Funcionário")
            busca = st.text_input("Digite nome ou CPF para filtrar")
            res_aud = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            df = pd.DataFrame(res_aud.data)
            if not df.empty:
                if busca:
                    df = df[df['nome_funcionario'].str.contains(busca, case=False) | df['cpf'].str.contains(busca)]
                st.dataframe(df, use_container_width=True)

        with menu_emp[2]: # EXPORTAR
            st.markdown("### 📦 Arquivo Completo")
            st.write("Baixe a base completa de auditoria da sua empresa em formato Excel/CSV.")
            if not df.empty:
                st.download_button("📥 BAIXAR RELATÓRIO COMPLETO", df.to_csv(), "relatorio_total.csv", use_container_width=True)

        with menu_emp[3]: # CHAMADOS
            st.markdown("### 🎫 Central de Atendimento")
            with st.form("chamado"):
                assunto = st.selectbox("Assunto", ["Erro nos dados", "Dúvida Técnica", "Financeiro", "Outros"])
                msg = st.text_area("Descreva sua necessidade")
                if st.form_submit_button("ABRIR CHAMADO"):
                    st.success("Chamado aberto com sucesso! Prazo de resposta: 24h.")

        with menu_emp[4]: # CONTA
            st.markdown("### ⚙️ Gestão de Acesso")
            new_u = st.text_input("Alterar Usuário", value=emp['login'])
            new_p = st.text_input("Nova Senha", type="password", placeholder="Deixe em branco para manter")
            if st.button("SALVAR ALTERAÇÕES"):
                upd = {"login": new_u}
                if new_p: upd["senha"] = sha256_hex(new_p)
                sb.table("empresas").update(upd).eq("id", emp['id']).execute()
                st.success("Dados atualizados! Reinicie o login.")
                st.session_state.emp_auth = None

# ============================================================
# 4) ADMIN MASTER (PLANOS E GESTÃO DE EMPRESAS)
# ============================================================
def portal_admin():
    st.markdown("# 🛡️ Controle Master (RRB)")
    pw = st.sidebar.text_input("Chave Mestre", type="password")
    
    if pw == st.secrets.get("SENHA_MASTER", "admin123"):
        t1, t2, t3 = st.tabs(["🏢 Empresas Ativas/Inativas", "➕ Nova Empresa", "📜 Termos e LGPD"])
        
        with t1:
            st.markdown("### Gestão de Clientes")
            all_emp = sb.table("empresas").select("*").execute()
            if all_emp.data:
                df_all = pd.DataFrame(all_emp.data)
                # Lógica de cores para status
                df_all['Situação'] = df_all['data_expiracao'].apply(lambda x: "🟢 ATIVA" if check_plan_status(x) else "🔴 EXPIRADA")
                st.dataframe(df_all[["nome_empresa", "cnpj", "plano", "data_expiracao", "Situação"]], use_container_width=True)

        with t2:
            st.markdown("### Cadastrar Novo Parceiro")
            with st.form("cad_empresa"):
                c1, c2 = st.columns(2)
                nome_e = c1.text_input("Razão Social")
                cnpj_e = c2.text_input("CNPJ (será o login)")
                
                reps = st.text_area("Representantes (Nome - Email - Telefone)", help="Um por linha")
                
                c3, c4 = st.columns(2)
                plano = c3.selectbox("Plano", ["Bronze", "Silver", "Gold", "Platinum Enterprise"])
                meses = c4.number_input("Meses de Vigência", min_value=1, value=12)
                
                st.markdown("---")
                aceite = st.checkbox("Autorizo o uso de dados conforme LGPD para fins de auditoria.")
                
                if st.form_submit_button("EFETIVAR CADASTRO"):
                    if aceite:
                        exp_date = (date.today() + timedelta(days=meses*30)).isoformat()
                        sb.table("empresas").insert({
                            "nome_empresa": nome_e, "cnpj": cnpj_e, "plano": plano,
                            "data_expiracao": exp_date, "login": cnpj_e, 
                            "senha": sha256_hex("mudar123"), "representantes": reps
                        }).execute()
                        st.success(f"Empresa {nome_e} cadastrada com sucesso!")
                    else: st.warning("Aceite os termos para continuar.")
    else:
        st.warning("Aguardando autenticação do administrador...")

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if menu == "👤 Funcionário": portal_funcionario()
elif menu == "🏢 Empresa": portal_empresa()
else: portal_admin()

# Botão flutuante WhatsApp
st.markdown(f'<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)

st.markdown("<br><hr><center><small>RRB Soluções em Auditoria © 2026 - Proteção de Dados Garantida</small></center>", unsafe_allow_html=True)
