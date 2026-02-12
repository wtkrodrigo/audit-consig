import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta
import io

# ============================================================
# 0) CONFIGURAÇÃO E ESTILO
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_sb()

def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))

# CSS Restaurado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stMetric { background: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.15); border-radius: 16px; padding: 20px; }
    .wpp-fab { position: fixed; bottom: 30px; right: 30px; background: #25D366; color: white !important; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; z-index: 1000; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) PORTAL DO FUNCIONÁRIO (FIX: CALENDÁRIO AMPLO)
# ============================================================
def portal_funcionario():
    st.markdown("# 🛡️ Área do Colaborador")
    
    with st.container():
        c1, c2, c3 = st.columns([2,2,1])
        cpf_in = c1.text_input("🔍 Digite seu CPF")
        
        # CORREÇÃO DA DATA: Definindo min_value e max_value para liberar todos os anos
        nasc_in = c2.date_input(
            "📅 Data de Nascimento", 
            format="DD/MM/YYYY",
            min_value=date(1900, 1, 1),
            max_value=date(2100, 12, 31)
        )
        tel_in = c3.text_input("📱 Fim do Telefone (4 dígitos)", max_chars=4)

    if st.button("📊 ANALISAR SITUAÇÃO", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).execute()
        
        if res.data:
            d = res.data[0]
            # Comparação robusta de strings
            data_banco = str(d.get("data_nascimento"))[:10]
            data_usuario = nasc_in.strftime("%Y-%m-%d")

            if data_banco == data_usuario:
                st.balloons()
                st.success(f"Olá, {d.get('nome_funcionario')}!")
                
                k1, k2, k3, k4 = st.columns(4)
                v_rh = float(d.get('valor_rh', 0))
                v_bnc = float(d.get('valor_banco', 0))
                diff = v_rh - v_bnc
                
                k1.metric("📌 Valor em Folha", f"R$ {v_rh:,.2f}")
                k2.metric("🏦 Valor no Banco", f"R$ {v_bnc:,.2f}")
                k3.metric("⚖️ Diferença", f"R$ {diff:,.2f}", delta=diff, delta_color="inverse")
                k4.metric("📈 Status", "✅ CONFORME" if abs(diff) < 1.0 else "⚠️ DIVERGENTE")
            else:
                st.error(f"❌ Data incorreta. (Dica: Use o ano correto no topo do calendário)")
        else:
            st.warning("⚠️ CPF não encontrado.")

# ============================================================
# 2) PORTAL DA EMPRESA (FIX: ERRO DASHBOARD)
# ============================================================
def portal_empresa():
    if "emp_auth" not in st.session_state: st.session_state.emp_auth = None

    if not st.session_state.emp_auth:
        u = st.text_input("CNPJ")
        p = st.text_input("Senha", type="password")
        if st.button("LOGIN"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and sha256_hex(p) == q.data[0].get("senha"):
                st.session_state.emp_auth = q.data[0]
                st.rerun()
    else:
        emp = st.session_state.emp_auth
        st.sidebar.write(f"Empresa: {emp['nome_empresa']}")
        t = st.tabs(["📊 Dashboard", "🔍 Pesquisa", "📥 Exportar", "⚙️ Conta"])

        res = sb.table("resultados_auditoria").eq("nome_empresa", emp['nome_empresa']).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

        with t[0]: # Dashboard
            if not df.empty:
                # CORREÇÃO DASHBOARD: Garantindo que valores sejam números para o gráfico
                df['valor_rh'] = pd.to_numeric(df['valor_rh'], errors='coerce').fillna(0)
                df['valor_banco'] = pd.to_numeric(df['valor_banco'], errors='coerce').fillna(0)
                df['diferenca'] = df['valor_rh'] - df['valor_banco']
                
                c1, c2 = st.columns(2)
                c1.metric("Total", len(df))
                erros = len(df[df['diferenca'].abs() > 1.0])
                c2.metric("Divergências", erros)
                
                st.bar_chart(df.set_index('nome_funcionario')[['valor_rh', 'valor_banco']])
            else: st.info("Sem dados.")
        
        with t[3]:
            if st.button("Sair"):
                st.session_state.emp_auth = None
                st.rerun()

# ============================================================
# 3) ADMIN MASTER
# ============================================================
def portal_admin():
    st.markdown("# ⚙️ Admin Master")
    if st.sidebar.text_input("Chave", type="password") == st.secrets.get("SENHA_MASTER", "admin123"):
        t1, t2, t3 = st.tabs(["🏢 Empresas", "➕ Novo", "📤 Upload"])
        
        with t1:
            all_emp = sb.table("empresas").select("*").execute()
            if all_emp.data:
                st.dataframe(pd.DataFrame(all_emp.data)[["nome_empresa", "cnpj", "plano", "data_expiracao"]], use_container_width=True)

        with t2:
            with st.form("cad"):
                nome = st.text_input("Razão Social")
                cnpj = st.text_input("CNPJ")
                if st.form_submit_button("CADASTRAR"):
                    exp = (date.today() + timedelta(days=365)).isoformat()
                    sb.table("empresas").insert({"nome_empresa": nome, "cnpj": cnpj, "data_expiracao": exp, "login": cnpj, "senha": sha256_hex("mudar123")}).execute()
                    st.success("Cadastrada!")

        with t3:
            st.subheader("📤 Upload CSV")
            emps = sb.table("empresas").select("nome_empresa").execute()
            dest = st.selectbox("Empresa Destino", [e['nome_empresa'] for e in emps.data])
            file = st.file_uploader("CSV", type="csv")
            if file and st.button("Sincronizar"):
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
                st.success("Pronto!")

# ============================================================
# MAIN
# ============================================================
nav = st.sidebar.radio("Menu", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])
if nav == "👤 Funcionário": portal_funcionario()
elif nav == "🏢 Empresa": portal_empresa()
else: portal_admin()
