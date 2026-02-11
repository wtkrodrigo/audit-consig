import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; box-shadow: 0 2px 5px #0001; }
    .header { display: flex; align-items: center; gap: 12px; background: white; padding: 18px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px #0000000d; }
    .shield { font-size: 38px; color: #002D62; border-right: 2px solid #eee; padding-right: 15px; line-height: 1; }
    .brand { font-weight: 900; font-size: 26px; color: #002D62; line-height: 1; }
    .dot { color: #d90429; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="header"><div class="shield">🛡️</div><div class="brand">RRB<span class="dot">.</span>SOLUÇÕES</div></div>', unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro de conexão com o banco."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. MÓDULO FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta ao Laudo de Auditoria")
    cpf_in = st.text_input("Digite apenas os números do seu CPF")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR") and cpf:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
        if r.data:
            d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("Folha RH", f"R$ {d['valor_rh']:.2f}")
            c2.metric("Base Banco", f"R$ {d['valor_banco']:.2f}")
            if d['diferenca'] == 0: st.info("✅ Conformidade Detectada: Seus descontos estão corretos.")
            else: st.error(f"❌ Divergência Detectada: Diferença de R$ {abs(d['diferenca']):.2f}")
        else: st.warning("Dados não localizados. Verifique o CPF ou fale com seu RH.")

# 2. MÓDULO EMPRESA (CLIENTE)
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Usuário"), st.text_input("Senha", type='password')
        if st.button("Acessar Painel"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.link = q.data[0].get('link_planilha', "")
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        st.subheader(f"Gestão de Auditoria: {st.session_state.n}")
        st.info("Os dados são extraídos automaticamente da sua Planilha Google configurada.")
        if st.button("🔄 SINCRONIZAR E PUBLICAR AGORA"):
            if st.session_state.link:
                try:
                    df = pd.read_csv(st.session_state.link)
                    df['dif'] = df['valor_rh'] - df['valor_banco']
                    sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.n).execute()
                    for _, r in df.iterrows():
                        pl = {"nome_empresa": st.session_state.n, "cpf": str(r['cpf']), "nome_funcionario": r['nome'], 
                              "valor
