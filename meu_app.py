import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB", layout="wide", page_icon="🛡️")
st.markdown("""<style>
    .main { background: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #002D62; box-shadow: 0 2px 5px #0001; }
    .header { display: flex; align-items: center; gap: 12px; background: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 5px #0001; }
    .shield { font-size: 30px; border-right: 2px solid #eee; padding-right: 15px; }
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
    st.subheader("Consulta de Transparência")
    cpf_in = st.text_input("Digite o CPF")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR") and cpf:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
        if r.data:
            d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("Folha RH", f"R$ {d['valor_rh']}")
            c2.metric("Banco", f"R$ {d['valor_banco']}")
            if d['diferenca'] == 0: st.info("✅ Tudo em dia")
            else: st.error(f"❌ Diferença: R$ {abs(d['diferenca'])}")
        else: st.warning("Não encontrado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                exp = datetime.strptime(q.data[0]['data_expiracao'], "%Y-%m-%d")
                if datetime.now() > exp: st.error("Acesso Expirado")
                else: st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']; st.rerun()
            else: st.error("Login Inválido")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        f1, f2 = st.file_uploader("RH (CSV)"), st.file_uploader("Banco (CSV)")
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf')
            res['dif'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            st.metric("Total de Funcionários", len(res))
            st.dataframe(res, use_container_width=True)
            if st.button("🚀 PUBLICAR"):
                sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.n).execute()
                for _, r in res.iterrows():
                    pl = {"nome_empresa": st.session_state.n, "cpf": str(r['cpf']), "nome_funcionario": r['nome'], "valor_rh": float(r['valor_descontado_rh']), "valor_banco": float(r['valor_devido_banco']), "diferenca": float(r['dif']), "status": "OK" if r['dif']==0 else "ERRO"}
                    sb.table("resultados_auditoria").insert(pl).execute()
                st.success("Dados publicados!")

# 3. ADMIN
elif m == "⚙️ Admin":
    pw = st.text_input("Senha Master", type='password')
    if pw and pw == st.secrets.get("SENHA_MASTER"):
        st.markdown("### 📝 Cadastro de Empresa")
        with st.form("cad_completo"):
            c1, c2 = st.columns(2)
            with c1:
                nome_emp = st.text_input("Razão Social")
                cnpj = st.text_input("CNPJ")
                rep = st.text_input("Representante")
            with c2:
                tel = st.text_input("Telefone")
                end = st.text_input("Endereço")
                dias = st.number_input("Dias de Acesso", 1, 365, 30)
            u_log, s_log = st.text_input("Usuário"), st.text_input("Senha", type='password')
            if st.form_submit_button("FINALIZAR CADASTRO"):
                if nome_emp and u_log and s_log:
                    v = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
                    dados = {"nome_empresa": nome_emp, "cnpj": cnpj, "representante": rep, "telefone": tel, "endereco": end, "login": u_log, "senha": h(s_log), "data_expiracao": v}
                    sb.table("empresas").insert(dados).execute()
                    st.success(f"Ativo até {v}")
