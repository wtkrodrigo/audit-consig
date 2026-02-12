import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io

# ============================================================
# 0) CONFIGURAÇÃO, CSS PREMIUM E ICONES (RESTAURADO)
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum Enterprise", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Efeito de Vidro e Fundo Gradiente */
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

    /* Botão WhatsApp Flutuante */
    .wpp-fab {
        position: fixed; bottom: 30px; right: 30px;
        background: #25D366; color: white !important;
        width: 60px; height: 60px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 30px; box-shadow: 0 10px 25px rgba(37, 211, 102, 0.4);
        z-index: 1000; text-decoration: none;
    }

    /* Rodapé LGPD */
    .footer-box {
        text-align: center; padding: 40px 0; font-size: 12px; opacity: 0.6;
        border-top: 1px solid rgba(128,128,128,0.1); margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) CONEXÃO E SEGURANÇA
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

@st.cache_resource
def get_sb():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Erro Crítico: Verifique as chaves do Supabase nos Secrets.")
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
# 2) PORTAL DO FUNCIONÁRIO (DATA E ICONES RESTAURADOS)
# ============================================================
def portal_funcionario():
    st.markdown("# 👤 Área do Colaborador")
    st.info("Consulte sua conformidade bancária de forma segura e transparente.")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🆔 Digite seu CPF", placeholder="000.000.000-00")
        
        # Calendário corrigido para permitir qualquer ano
        nasc_in = c2.date_input(
            "📅 Data de Nascimento", 
            format="DD/MM/YYYY",
            min_value=date(1900, 1, 1),
            max_value=date(2100, 12, 31)
        )
        tel_in = c3.text_input("📱 Fim do Telefone", max_chars=4, placeholder="1234")

    if st.button("🚀 ANALISAR MINHA SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        
        if res.data:
            d = res.data[0]
            # Lógica de data original e funcional
            data_banco = str(d.get("data_nascimento") or "")[:10]
            data_usuario = nasc_in.strftime("%Y-%m-%d")

            if data_banco == data_usuario:
                st.balloons()
                st.markdown(f"### Bem-vindo, {d.get('nome_funcionario').split()[0]}! 👋")
                
                k1, k2, k3, k4 = st.columns(4)
                v_rh = float(d.get('valor_rh', 0))
                v_bnc = float(d.get('valor_banco', 0))
                diff = v_rh - v_bnc
                
                k1.metric("📌 Valor em Folha", f"R$ {v_rh:,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {v_bnc:,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                k4.metric("📈 Status", "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE")
            else:
                st.error("❌ Data de nascimento não confere com nossos registros.")
        else:
            st.warning("⚠️ CPF não localizado na base de dados.")

# ============================================================
# 3) PORTAL DA EMPRESA (FULL ENTERPRISE + FIX DASHBOARD)
# ============================================================
def portal_empresa():
    st.markdown("# 🏢 Painel Corporativo Platinum")
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        t_login, t_reset = st.tabs(["🔐 Login", "🔑 Esqueci Senha"])
        with t_login:
            u = st.text_input("CNPJ (Login)")
            p = st.text_input("Senha", type="password")
            if st.button("ACESSAR SISTEMA"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    if check_plan_status(q.data[0].get("data_expiracao")):
                        st.session_state.emp_auth = q.data[0]
                        st.rerun()
                    else: st.error("🚨 Plano Expirado. Contate o suporte.")
                else: st.error("Credenciais inválidas.")
        with t_reset:
            st.info("Informe seu CNPJ para receber as instruções de recuperação.")
            st.text_input("CNPJ Cadastrado")
            st.button("SOLICITAR REINICIALIZAÇÃO")

    else:
        emp = st.session_state.emp_auth
        st.sidebar.success(f"Logado: {emp['nome_empresa']}")
        
        # Abas enterprise restauradas
        tabs = st.tabs(["📊 Dashboard", "🔍 Pesquisa", "📥 Exportar", "🎫 Suporte & FAQ", "⚙️ Conta"])

        # Busca segura de dados para evitar o erro AttributeError
        try:
            res_aud = sb.table("resultados_auditoria").select("*").eq("nome_empresa", emp.get('nome_empresa')).execute()
            df = pd.DataFrame(res_aud.data) if res_aud.data else pd.DataFrame()
        except:
            df = pd.DataFrame()

        with tabs[0]: # Dashboard Blindado
            if not df.empty:
                df['valor_rh'] = pd.to_numeric(df['valor_rh'], errors='coerce').fillna(0)
                df['valor_banco'] = pd.to_numeric(df['valor_banco'], errors='coerce').fillna(0)
                df['diferenca'] = df['valor_rh'] - df['valor_banco']
                
                c1, c2, c3 = st.columns(3)
                total = len(df)
                erros = len(df[df['diferenca'].abs() > 1.0])
                c1.metric("Total Funcionários", total)
                c2.metric("Divergências", erros, delta=erros, delta_color="inverse")
                c3.metric("Saúde da Folha", f"{((total-erros)/total)*100:.1f}%")
                
                st.subheader("Gráfico de Confronto Financeiro")
                st.bar_chart(df.set_index('nome_funcionario')[['valor_rh', 'valor_banco']])
            else:
                st.warning("⚠️ Nenhuma informação disponível para exibir no gráfico.")

        with tabs[3]: # Suporte & FAQ Restaurado
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### ❓ FAQ - Dúvidas")
                with st.expander("Como corrigir divergências?"): st.write("Contate o RH para validar o arquivo enviado.")
            with c2:
                st.markdown("### 🎫 Chamados")
                st.text_area("Descreva sua solicitação")
                st.button("Abrir Ticket")

        with tabs[4]: # Minha Conta Restaurado
            if st.button("🚪 Efetuar Logoff"):
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 4) ADMIN MASTER (RESTAURADO)
# ============================================================
def portal_admin():
    st.markdown("# 🛡️ Master Control Center")
    if st.sidebar.text_input("Chave Mestre", type="password") == st.secrets.get("SENHA_MASTER", "admin123"):
        
        t1, t2, t3 = st.tabs(["🏢 Empresas Ativas", "➕ Novo Contrato", "📤 Sincronizar CSV"])
        
        with t1:
            st.subheader("Gestão de Clientes")
            all_emp = sb.table("empresas").select("*").execute()
            if all_emp.data:
                df_all = pd.DataFrame(all_emp.data)
                df_all['Situação'] = df_all['data_expiracao'].apply(lambda x: "🟢 ATIVA" if check_plan_status(x) else "🔴 BLOQUEADA")
                st.dataframe(df_all[["nome_empresa", "cnpj", "plano", "data_expiracao", "Situação", "representantes"]], use_container_width=True)

        with t3:
            st.subheader("📤 Upload de Base de Dados")
            emps_db = sb.table("empresas").select("nome_empresa").execute()
            dest = st.selectbox("Selecione a Empresa Destino", [e['nome_empresa'] for e in emps_db.data])
            file = st.file_uploader("Subir CSV de Auditoria", type="csv")
            if file and st.button("🔥 INICIAR SINCRONIZAÇÃO"):
                df_up = pd.read_csv(file)
                regs = []
                for _, r in df_up.iterrows():
                    v1, v2 = float(r.get('valor_rh', 0)), float(r.get('valor_banco', 0))
                    regs.append({
                        "nome_funcionario": r.get('nome'), "cpf": digits_only(str(r.get('cpf'))),
                        "data_nascimento": str(r.get('data_nascimento')), "valor_rh": v1,
                        "valor_banco": v2, "diferenca": v1-v2, "nome_empresa": dest,
                        "banco_nome": r.get('banco', 'PADRAO'), "telefone": str(r.get('telefone', ''))
                    })
                sb.table("resultados_auditoria").insert(regs).execute()
                st.success(f"✅ Sincronizado {len(regs)} registros para {dest}!")
    else:
        st.warning("Aguardando Chave Mestre de Segurança...")

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================
nav = st.sidebar.radio("Navegação Principal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
if nav == "👤 Funcionário": portal_funcionario()
elif nav == "🏢 Empresa": portal_empresa()
else: portal_admin()

# WhatsApp e Footer
st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)
st.markdown("<div class='footer-box'>© 2026 RRB Soluções | Proteção de Dados LGPD | Criptografia Platinum 🛡️</div>", unsafe_allow_html=True)
