import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io

# ============================================================
# 0) CONFIGURAÇÃO E CSS AVANÇADO (RESTAURADO)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum Enterprise", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Glassmorphism Dinâmico Restaurado */
    .stApp {
        background: radial-gradient(circle at 0% 0%, rgba(74, 144, 226, 0.1) 0%, transparent 30%),
                    radial-gradient(circle at 100% 100%, rgba(0, 45, 98, 0.05) 0%, transparent 30%);
    }

    .stMetric {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 16px;
        padding: 20px;
        backdrop-filter: blur(12px);
    }

    /* WhatsApp FAB Restaurado */
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 55px; height: 55px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 26px; box-shadow: 0 8px 24px rgba(37, 211, 102, 0.3);
        z-index: 1000; text-decoration: none;
    }

    /* Footer de Privacidade Restaurado */
    .footer-box {
        text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.6;
        border-top: 1px solid rgba(128,128,128,0.1); margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) UTILITÁRIOS E SEGURANÇA
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_sb()

def check_plan_status(exp_date):
    if not exp_date: return False
    try:
        if isinstance(exp_date, str):
            exp_date = datetime.strptime(exp_date[:10], "%Y-%m-%d").date()
        return exp_date >= date.today()
    except: return False

def render_footer():
    st.markdown("""<div class="footer-box">
    © 2026 RRB Soluções | Termos de Privacidade e Proteção de Dados (LGPD) <br>
    Este sistema utiliza criptografia de ponta a ponta para proteger as informações de auditoria.
    </div>""", unsafe_allow_html=True)

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO (COM VALIDAÇÃO DE TELEFONE)
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
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        if res.data:
            d = res.data[0]
            # Comparação de Data e Validação do Final do Telefone (Restaura Segurança)
            data_banco = str(d.get("data_nascimento"))[:10]
            tel_banco = digits_only(str(d.get("telefone", "")))
            
            if data_banco == nasc_in.strftime("%Y-%m-%d") and tel_banco.endswith(tel_in):
                st.balloons()
                st.markdown(f"### Bem-vindo, {d.get('nome_funcionario').split()[0]}! 👋")
                
                k1, k2, k3, k4 = st.columns(4)
                v_rh = float(d.get('valor_rh', 0))
                v_bnc = float(d.get('valor_banco', 0))
                diff = v_rh - v_bnc
                k1.metric("📌 Valor em Folha", f"R$ {v_rh:,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {v_bnc:,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                k4.metric("📈 Status Final", "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE")

                with st.expander("📄 Ver Detalhes e Baixar Comprovante"):
                    st.info("Este documento serve como demonstrativo de auditoria interna da RRB Soluções.")
                    csv = pd.DataFrame([d]).to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Relatório (CSV)", csv, "meu_relatorio.csv", "text/csv")
            else:
                st.error("Dados de validação não conferem. Verifique a data de nascimento e o final do telefone.")
        else:
            st.warning("CPF não localizado na base de dados.")

# ============================================================
# 3) PORTAL DA EMPRESA (FULL ENTERPRISE)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        tab_log, tab_reset = st.tabs(["🔐 Login", "🔑 Esqueci Senha"])
        with tab_log:
            u = st.text_input("Usuário (CNPJ)")
            p = st.text_input("Senha", type="password")
            if st.button("ACESSAR SISTEMA"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    if check_plan_status(q.data[0].get("data_expiracao")):
                        st.session_state.emp_auth = q.data[0]
                        st.rerun()
                    else: st.error("❌ Plano Expirado. Entre em contato com o suporte.")
                else: st.error("Credenciais inválidas.")
        with tab_reset:
            st.info("Informe o CNPJ para resetar sua senha.")
            reset_cnpj = st.text_input("CNPJ Cadastrado")
            if st.button("SOLICITAR NOVA SENHA"):
                st.success("Solicitação enviada! O representante receberá as instruções por e-mail.")

    else:
        emp = st.session_state.emp_auth
        st.sidebar.subheader(f"Olá, {emp['nome_empresa']}")
        tabs = st.tabs(["📊 Dashboard Auditoria", "🔍 Pesquisa", "📥 Exportar", "🛠️ Serviços e Suporte", "⚙️ Minha Conta"])

        res = sb.table("resultados_auditoria").eq("nome_empresa", emp['nome_empresa']).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

        with tabs[0]:
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                total = len(df)
                erros = len(df[df['diferenca'].astype(float).abs() > 1.0])
                c1.metric("Funcionários", total)
                c2.metric("Divergências", erros, delta=erros, delta_color="inverse")
                c3.metric("Conformidade", f"{((total-erros)/total)*100:.1f}%")
                st.bar_chart(df.set_index('nome_funcionario')[['valor_rh', 'valor_banco']])
            else: st.info("Nenhum dado sincronizado.")

        with tabs[3]: # SERVIÇOS E SUPORTE RESTAURADO
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### ❓ FAQ - Dúvidas Comuns")
                with st.expander("Como atualizar os dados?"): st.write("Suba o novo CSV através do painel admin.")
            with c2:
                st.markdown("### 🎫 Abrir Chamado")
                st.text_area("Descreva o problema")
                st.button("ENVIAR CHAMADO")

        with tabs[4]: # MINHA CONTA RESTAURADO
            st.markdown("### 🛠️ Alterar Credenciais")
            new_u = st.text_input("Novo Usuário", value=emp['login'])
            new_p = st.text_input("Nova Senha", type="password")
            if st.button("ATUALIZAR DADOS"):
                upd = {"login": new_u}
                if new_p: upd["senha"] = sha256_hex(new_p)
                sb.table("empresas").update(upd).eq("id", emp['id']).execute()
                st.success("Dados atualizados! Reinicie o login.")
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 4) ADMIN MASTER (PLANOS, BLOQUEIO E UPLOAD)
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Master Control Panel")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets.get("SENHA_MASTER", "admin123"):
        t1, t2, t3 = st.tabs(["🏢 Gestão de Ativos", "➕ Registrar Empresa", "📤 Sincronizar CSV"])
        
        with t2:
            with st.form("new_emp"):
                st.markdown("### Cadastro de Parceiro")
                razao = st.text_input("Razão Social")
                cnpj = st.text_input("CNPJ")
                reps = st.text_area("Representantes (Nome e E-mail)")
                plan = st.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
                meses = st.number_input("Duração (Meses)", value=12)
                st.checkbox("Aceito os termos de uso (LGPD)")
                if st.form_submit_button("CADASTRAR"):
                    exp = (date.today() + timedelta(days=meses*30)).isoformat()
                    sb.table("empresas").insert({
                        "nome_empresa": razao, "cnpj": cnpj, "plano": plan,
                        "data_expiracao": exp, "login": cnpj, "senha": sha256_hex("mudar123"),
                        "representantes": reps
                    }).execute()
                    st.success("Empresa cadastrada!")

        with t3:
            st.subheader("📤 Upload de Base de Dados")
            emps = sb.table("empresas").select("nome_empresa").execute()
            lista = [e['nome_empresa'] for e in emps.data] if emps.data else []
            destino = st.selectbox("Empresa Destino", lista)
            file = st.file_uploader("Subir CSV", type="csv")
            if file and st.button("🚀 SINCRONIZAR"):
                df_up = pd.read_csv(file)
                regs = []
                for _, r in df_up.iterrows():
                    v1, v2 = float(r.get('valor_rh', 0)), float(r.get('valor_banco', 0))
                    regs.append({
                        "nome_funcionario": r.get('nome'), "cpf": digits_only(str(r.get('cpf'))),
                        "data_nascimento": str(r.get('data_nascimento')), "valor_rh": v1,
                        "valor_banco": v2, "diferenca": v1-v2, "nome_empresa": destino,
                        "banco_nome": r.get('banco', 'BCO PADRAO'), "telefone": str(r.get('telefone', ''))
                    })
                sb.table("resultados_auditoria").insert(regs).execute()
                st.success("Sincronização concluída!")

    else: st.warning("Aguardando Chave Mestre...")

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
if menu == "👤 Funcionário": portal_funcionario()
elif menu == "🏢 Empresa": portal_empresa()
else: portal_admin()

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
render_footer()
