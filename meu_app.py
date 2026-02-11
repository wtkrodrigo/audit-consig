import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f4f7f9; }
    .stMetric { background: white; padding: 20px; border-radius: 15px; border-left: 6px solid #002D62; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .logo-container { text-align: center; background: white; padding: 20px; border-radius: 15px; margin-bottom: 25px; }
    .logo-rrb { font-weight: 900; font-size: 30px; color: #002D62; }
    @media (max-width: 640px) { .stButton>button { width: 100%; height: 55px; font-size: 18px; } }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="logo-container"><span class="logo-rrb">RRB<span style="color:#d90429">.</span>SOLUÇÕES</span></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()
def c_h(p, h_t): return h(p) == h_t

# --- NAVEGAÇÃO ---
menu = ["👤 Funcionário (App)", "🏢 Empresa (Gestão)", "⚙️ Admin"]
m = st.sidebar.selectbox("Módulo", menu)

# 1. FUNCIONÁRIO
if m == "👤 Funcionário (App)":
    st.subheader("🔎 Consulta de Transparência")
    cpf_in = st.text_input("Seu CPF (apenas números)")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR CONSIGNADO"):
        if cpf:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
            if r.data:
                d = r.data[0]
                st.success(f"Olá, {d['nome_funcionario']}!")
                c1, c2 = st.columns(2)
                c1.metric("Em Folha", f"R$ {d['valor_rh']}")
                c2.metric("No Banco", f"R$ {d['valor_banco']}")
                if d['diferenca'] == 0: st.info("✅ Tudo correto!")
                else: st.error(f"❌ Divergência: R$ {abs(d['diferenca'])}")
            else: st.warning("CPF não localizado.")

# 2. EMPRESA
elif m == "🏢 Empresa (Gestão)":
    if 'auth' not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and c_h(p, q.data[0]['senha']):
                # VERIFICA EXPIRAÇÃO
                exp = datetime.strptime(q.data[0]['data_expiracao'], "%Y-%m-%d")
                if datetime.now() > exp: st.error("Acesso expirado. Contate a RRB.")
                else:
                    st.session_state.auth, st.session_state.emp_nome = True, q.data[0]['nome_empresa']
                    st.rerun()
            else: st.error("Dados inválidos.")
    else:
        st.subheader(f"Gestão: {st.session_state.emp_nome}")
        f1, f2 = st.file_uploader("Arquivo RH"), st.file_uploader("Arquivo BANCO")
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf')
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "OK" if x == 0 else "ERRO")
            
            st.markdown("### 📊 Resumo da Auditoria")
            k1, k2, k3 = st.columns(3)
            k1.metric("Total CPFs", len(res))
            k2.metric("Com Erros", len(res[res['Status'] == "ERRO"]))
            k3.metric("Impacto", f"R$ {res['Diferença'].abs().sum():.2f}")
            
            st.dataframe(res, use_container_width=True)
            if st.button("🚀 PUBLICAR PARA FUNCIONÁRIOS"):
                sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.emp_nome).execute()
                for _, r in res.iterrows():
                    pl = {"nome_empresa": st.session_state.emp_nome, "cpf": str(r['cpf']), "nome_funcionario": r['nome'], "valor_rh": float(r['valor_descontado_rh']), "valor_banco": float(r['valor_devido_banco']), "diferenca": float(r['Diferença']), "status": r['Status']}
                    sb.table("resultados_auditoria").insert(pl).execute()
                st.success("Publicado!")

# 3. ADMIN (CORRIGIDO)
elif m == "⚙️ Admin":
    st.subheader("🛠️ Painel de Controle Master")
    senha_m = st.text_input("Digite a Senha Master", type='password
