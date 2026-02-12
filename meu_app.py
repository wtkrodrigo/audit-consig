import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io

# ============================================================
# 0) CONFIGURAÇÃO E ESTILO PLATINUM (RESTAURADO)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum Enterprise", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stMetric { background: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.15); border-radius: 16px; padding: 20px; }
    .wpp-fab { position: fixed; bottom: 30px; right: 30px; background: #25D366; color: white !important; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4); z-index: 1000; text-decoration: none; }
    .footer-box { text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.6; border-top: 1px solid rgba(128,128,128,0.1); margin-top: 40px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) CONEXÃO E UTILITÁRIOS
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

# ============================================================
# 2) PORTAL DO FUNCIONÁRIO (VOLTANDO À LÓGICA ORIGINAL)
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área do Colaborador")
    st.write("Verifique sua situação de forma segura.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 Digite seu CPF")
        nasc_in = c2.date_input("📅 Data de Nascimento", format="DD/MM/YYYY")
        tel_in = c3.text_input("📱 Fim do Telefone", max_chars=4)

    if st.button("📊 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        
        if res.data:
            d = res.data[0]
            # RESTAURADO: Lógica de data original que você tinha e funcionava
            data_banco = d.get("data_nascimento")
            data_usuario = nasc_in.strftime("%Y-%m-%d")

            if str(data_banco) == str(data_usuario):
                st.balloons()
                st.success(f"Olá, {d.get('nome_funcionario')}!")
                
                k1, k2, k3, k4 = st.columns(4)
                v_rh, v_bnc = float(d.get('valor_rh', 0)), float(d.get('valor_banco', 0))
                diff = v_rh - v_bnc
                k1.metric("📌 Valor em Folha", f"R$ {v_rh:,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {v_bnc:,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                k4.metric("📈 Status", "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE")
            else:
                st.error("❌ Data de nascimento incorreta para este CPF.")
        else:
            st.warning("⚠️ CPF não localizado.")

# ============================================================
# 3) PORTAL DA EMPRESA (RESTAURANDO TODAS AS OPÇÕES)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo Platinum")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        t1, t2 = st.tabs(["🔐 Login", "🔑 Esqueci Senha"])
        with t1:
            u, p = st.text_input("CNPJ (Apenas números)"), st.text_input("Senha", type="password")
            if st.button("ACESSAR PAINEL"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    if check_plan_status(q.data[0].get("data_expiracao")):
                        st.session_state.emp_auth = q.data[0]
                        st.rerun()
                    else: st.error("🚨 Plano Expirado. Contate o Administrador.")
                else: st.error("Dados de acesso inválidos.")
    else:
        emp = st.session_state.emp_auth
        st.sidebar.markdown(f"### {emp['nome_empresa']}")
        
        # RESTAURADO: Todas as abas que haviam sumido
        tabs = st.tabs(["📊 Dashboard", "🔍 Pesquisa de Funcionário", "📥 Exportar Dados", "🎫 Suporte e FAQ", "⚙️ Minha Conta"])

        res_aud = sb.table("resultados_auditoria").eq("nome_empresa", emp['nome_empresa']).execute()
        df = pd.DataFrame(res_aud.data) if res_aud.data else pd.DataFrame()

        with tabs[0]: # Dashboard
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                total = len(df)
                erros = len(df[df['diferenca'].astype(float).abs() > 1.0])
                c1.metric("Funcionários", total)
                c2.metric("Divergências", erros, delta=erros, delta_color="inverse")
                c3.metric("Conformidade", f"{((total-erros)/total)*100:.1f}%")
                st.subheader("Confronto Financeiro")
                st.bar_chart(df.set_index('nome_funcionario')[['valor_rh', 'valor_banco']])
            else: st.info("⚠️ Aguardando sincronização de dados.")

        with tabs[1]: # Pesquisa
            st.subheader("🔍 Localizar Colaborador")
            termo = st.text_input("Nome ou CPF")
            if not df.empty:
                f_df = df[df['nome_funcionario'].str.contains(termo, case=False)] if termo else df
                st.dataframe(f_df, use_container_width=True)

        with tabs[2]: # Exportar
            st.subheader("📥 Exportar Relatórios")
            if not df.empty:
                st.download_button("📥 BAIXAR CSV COMPLETO", df.to_csv(index=False), "auditoria.csv")

        with tabs[3]: # Suporte
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### ❓ FAQ")
                with st.expander("Como ler o Dashboard?"): st.write("As barras mostram a diferença entre o enviado pelo RH e o recebido no banco.")
            with c2:
                st.markdown("### 🎫 Chamados")
                st.text_area("Descreva sua solicitação")
                st.button("Enviar")

        with tabs[4]: # Conta
            st.subheader("⚙️ Configurações")
            if st.button("Efetuar Logoff"):
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 4) ADMIN MASTER (RESTAURANDO GESTÃO E LISTA DE EMPRESAS)
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Sistema de Controle Master")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets.get("SENHA_MASTER", "admin123"):
        
        # RESTAURADO: As 3 abas essenciais
        t1, t2, t3 = st.tabs(["🏢 Empresas Ativas", "➕ Novo Contrato", "📤 Sincronizar CSV"])
        
        with t1:
            st.subheader("Gestão de Clientes")
            all_emp = sb.table("empresas").select("*").execute()
            if all_emp.data:
                df_all = pd.DataFrame(all_emp.data)
                df_all['Situação'] = df_all['data_expiracao'].apply(lambda x: "🟢 ATIVA" if check_plan_status(x) else "🔴 BLOQUEADA")
                # RESTAURADO: Visualização da tabela no admin
                st.dataframe(df_all[["nome_empresa", "cnpj", "plano", "data_expiracao", "Situação", "representantes"]], use_container_width=True)
            else:
                st.info("Nenhuma empresa no sistema.")

        with t2:
            with st.form("cad_master"):
                st.subheader("Registrar Novo Cliente")
                n, c = st.columns(2)
                nome = n.text_input("Razão Social")
                cnpj = c.text_input("CNPJ (Login)")
                reps = st.text_area("Representantes (Nome e E-mail)")
                plan = st.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
                if st.form_submit_button("CADASTRAR EMPRESA"):
                    exp = (date.today() + timedelta(days=365)).isoformat()
                    sb.table("empresas").insert({"nome_empresa": nome, "cnpj": cnpj, "plano": plan, "data_expiracao": exp, "login": cnpj, "senha": sha256_hex("mudar123"), "representantes": reps}).execute()
                    st.success("Empresa cadastrada com sucesso!")

        with t3:
            st.subheader("📤 Upload de Base Auditoria")
            emps = sb.table("empresas").select("nome_empresa").execute()
            lista = [e['nome_empresa'] for e in emps.data] if emps.data else []
            destino = st.selectbox("Selecione a Empresa", lista)
            file = st.file_uploader("Arquivo CSV", type="csv")
            if file and st.button("🚀 SINCRONIZAR DADOS"):
                df_up = pd.read_csv(file)
                registros = []
                for _, r in df_up.iterrows():
                    v1, v2 = float(r.get('valor_rh', 0)), float(r.get('valor_banco', 0))
                    registros.append({
                        "nome_funcionario": r.get('nome'), "cpf": digits_only(str(r.get('cpf'))),
                        "data_nascimento": str(r.get('data_nascimento')), "valor_rh": v1,
                        "valor_banco": v2, "diferenca": v1-v2, "nome_empresa": destino,
                        "banco_nome": r.get('banco', 'BCO PADRAO'), "telefone": str(r.get('telefone', ''))
                    })
                sb.table("resultados_auditoria").insert(registros).execute()
                st.success(f"Sucesso! {len(registros)} registros enviados.")
    else:
        st.warning("Aguardando Chave Mestre...")

# ============================================================
# EXECUÇÃO
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
if menu == "👤 Funcionário": portal_funcionario()
elif menu == "🏢 Empresa": portal_empresa()
else: portal_admin()

st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
st.markdown("<div class='footer-box'>© 2026 RRB Soluções | Proteção LGPD</div>", unsafe_allow_html=True)
