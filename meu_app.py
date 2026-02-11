import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB", layout="wide", page_icon="🛡️")

st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; }
    .header { display: flex; align-items: center; gap: 12px; background: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 5px #0001; }
    .shield { font-size: 30px; color: #002D62; border-right: 2px solid #eee; padding-right: 15px; }
    .brand { font-weight: 900; font-size: 22px; color: #002D62; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="header"><div class="shield">🛡️</div><div class="brand">RRB<span style="color:#d90429">.</span>SOLUÇÕES</div></div>', unsafe_allow_html=True)

# --- DB ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONÁRIO
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta")
    cpf_in = st.text_input("CPF (apenas números)")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR") and cpf:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
        if r.data:
            d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("Folha RH", f"R$ {d['valor_rh']:.2f}")
            c2.metric("Banco", f"R$ {d['valor_banco']:.2f}")
            if d['diferenca'] == 0: st.info("✅ Tudo em dia")
            else: st.error(f"❌ Erro: R$ {abs(d['diferenca']):.2f}")
        else: st.warning("Não encontrado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.button("🔄 ATUALIZAR PLANILHA"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df['dif'] = df['valor_rh'] - df['valor_banco']
                sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.n).execute()
                for _, r in df.iterrows():
                    row = {
                        "nome_empresa": st.session_state.n,
                        "cpf": str(r['cpf']),
                        "nome_funcionario": r['nome'],
                        "valor_rh": float(r['valor_rh']),
                        "valor_banco": float(r['valor_banco']),
                        "diferenca": float(r['dif']),
                        "status": "OK" if r['dif']==0 else "ERRO"
                    }
                    sb.table("resultados_auditoria").insert(row).execute()
                st.success("Sucesso!"); st.dataframe(df)
            except: st.error("Erro na leitura dos dados.")

# 3. ADMIN
elif m == "⚙️ Admin":
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad_rrb"):
            c1, c2 = st.columns(2)
            with c1:
                n_emp = st.text_input("Razão Social")
                n_cnp = st.text_input("CNPJ")
                n_rep = st.text_input("Representante")
            with c2:
                n_tel = st.text_input("Telefone")
                n_end = st.text_input("Endereço")
                n_dia = st.number_input("Dias", 1, 365, 30)
            st.markdown("---")
            n_lk = st.text_input("Link CSV Planilha")
            n_u = st.text_input("User Login")
            n_s = st.text_input("Pass Login", type='password')
            if st.form_submit_button("CADASTRAR"):
                exp = (datetime.now() + timedelta(days=n_dia)).strftime("%Y-%m-%d")
                # Dicionário quebrado em linhas para evitar o SyntaxError de corte
                d_ins = {
                    "nome_empresa": n_emp,
                    "cnpj": n_cnp,
                    "representante": n_rep,
                    "telefone": n_tel,
                    "endereco": n_end,
                    "login": n_u,
                    "senha": h(n_s),
                    "data_expiracao": exp,
                    "link_planilha": n_lk
                }
                sb.table("empresas").insert(d_ins).execute()
                st.success(f"Ativo até: {exp}")
