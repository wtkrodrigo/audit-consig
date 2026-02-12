import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io

# ============================================================
# 0) CONFIGURAÇÃO E CSS (DESIGN ENTERPRISE)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp {
        background: radial-gradient(circle at 0% 0%, rgba(74, 144, 226, 0.1) 0%, transparent 30%),
                    radial-gradient(circle at 100% 100%, rgba(0, 45, 98, 0.05) 0%, transparent 30%);
    }
    .stMetric { background: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.15); border-radius: 16px; padding: 20px; backdrop-filter: blur(12px); }
    .wpp-fab { position: fixed; bottom: 30px; right: 30px; background: #25D366; color: white !important; width: 55px; height: 55px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 26px; box-shadow: 0 8px 24px rgba(37, 211, 102, 0.3); z-index: 1000; text-decoration: none; }
    .footer-box { text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.6; border-top: 1px solid rgba(128,128,128,0.1); margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) UTILITÁRIOS E SEGURANÇA (BLINDAGEM)
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

@st.cache_resource
def get_sb():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("Erro na conexão com Supabase. Verifique os Secrets.")
        return None

sb = get_sb()

def check_plan_status(exp_date):
    if not exp_date: return False
    try:
        if isinstance(exp_date, str):
            exp_date = datetime.strptime(exp_date[:10], "%Y-%m-%d").date()
        return exp_date >= date.today()
    except: return False

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO (FIX: ERRO DE ENDSWITH E DATA)
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área do Colaborador")
    st.write("Consulte sua conformidade bancária.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 CPF", placeholder="000.000.000-00")
        nasc_in = c2.date_input("📅 Nascimento", format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Fim do Telefone", max_chars=4)

    if st.button("📊 ANALISAR", use_container_width=True):
        if not sb: return
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        
        if res.data:
            d = res.data[0]
            # Proteção contra valores Nulos (None)
            data_banco = str(d.get("data_nascimento") or "")[:10]
            tel_banco = digits_only(str(d.get("telefone") or ""))
            
            # Validação segura
            if data_banco == nasc_in.strftime("%Y-%m-%d") and (not tel_in or tel_banco.endswith(tel_in)):
                st.balloons()
                st.success(f"Bem-vindo, {d.get('nome_funcionario', 'Colaborador')}!")
                
                k1, k2, k3, k4 = st.columns(4)
                v_rh, v_bnc = float(d.get('valor_rh', 0)), float(d.get('valor_banco', 0))
                diff = v_rh - v_bnc
                k1.metric("📌 Valor em Folha", f"R$ {v_rh:,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {v_bnc:,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                k4.metric("📈 Status", "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE")
            else:
                st.error("❌ Dados de validação não conferem.")
        else:
            st.warning("⚠️ CPF não encontrado.")

# ============================================================
# 3) PORTAL DA EMPRESA (FIX: ERRO DE ATRIBUTO)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        t1, t2 = st.tabs(["🔐 Login", "🔑 Esqueci Senha"])
        with t1:
            u, p = st.text_input("CNPJ"), st.text_input("Senha", type="password")
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
        st.sidebar.subheader(f"Olá, {emp['nome_empresa']}")
        tabs = st.tabs(["📊 Dashboard", "🔍 Pesquisa", "📥 Exportar", "🛠️ Suporte", "⚙️ Conta"])

        # Chamada segura para o banco
        try:
            res = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp['nome_empresa']).execute()
            df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        except:
            df = pd.DataFrame()

        with tabs[0]: # Dashboard
            if not df.empty:
                c1, c2 = st.columns(2)
                c1.metric("Funcionários", len(df))
                st.bar_chart(df.set_index('nome_funcionario')[['valor_rh', 'valor_banco']])
            else: st.info("Sem dados sincronizados.")

        with tabs[4]: # Conta
            if st.button("Sair"):
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 4) ADMIN MASTER (FIX: LISTA DE EMPRESAS ATIVAS)
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Admin Master")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets.get("SENHA_MASTER", "admin123"):
        t1, t2, t3 = st.tabs(["🏢 Empresas Ativas", "➕ Novo Contrato", "📤 Sincronizar CSV"])
        
        with t1:
            st.subheader("Gestão de Clientes")
            all_emp = sb.table("empresas").select("*").execute()
            if all_emp.data:
                df_all = pd.DataFrame(all_emp.data)
                # Adiciona coluna de status visual
                df_all['Situação'] = df_all['data_expiracao'].apply(lambda x: "🟢 ATIVA" if check_plan_status(x) else "🔴 BLOQUEADA")
                # RESTAURA A TABELA QUE ESTAVA SUMIDA
                st.dataframe(df_all[["nome_empresa", "cnpj", "plano", "data_expiracao", "Situação", "representantes"]], use_container_width=True)
            else:
                st.info("Nenhuma empresa cadastrada.")

        with t2: # Cadastro
            with st.form("cad"):
                n, c = st.columns(2)
                nome = n.text_input("Razão Social")
                cnpj = c.text_input("CNPJ")
                reps = st.text_area("Representantes")
                if st.form_submit_button("CADASTRAR"):
                    exp = (date.today() + timedelta(days=365)).isoformat()
                    sb.table("empresas").insert({"nome_empresa": nome, "cnpj": cnpj, "data_expiracao": exp, "login": cnpj, "senha": sha256_hex("mudar123"), "representantes": reps}).execute()
                    st.success("Cadastrado!")

        with t3: # Upload
            st.subheader("📤 Upload CSV")
            emps = sb.table("empresas").select("nome_empresa").execute()
            dest = st.selectbox("Empresa Destino", [e['nome_empresa'] for e in emps.data])
            file = st.file_uploader("Arquivo", type="csv")
            if file and st.button("SINCRONIZAR"):
                df_up = pd.read_csv(file)
                regs = []
                for _, r in df_up.iterrows():
                    v1, v2 = float(r.get('valor_rh',0)), float(r.get('valor_banco',0))
                    regs.append({
                        "nome_funcionario": r.get('nome'), "cpf": digits_only(str(r.get('cpf'))),
                        "data_nascimento": str(r.get('data_nascimento')), "valor_rh": v1,
                        "valor_banco": v2, "diferenca": v1-v2, "nome_empresa": dest, "telefone": str(r.get('telefone', ''))
                    })
                sb.table("resultados_auditoria").insert(regs).execute()
                st.success("Sincronizado!")

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
if menu == "👤 Funcionário": portal_funcionario()
elif menu == "🏢 Empresa": portal_empresa()
else: portal_admin()

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
st.markdown("<div class='footer-box'>© 2026 RRB Soluções | Proteção LGPD</div>", unsafe_allow_html=True)
