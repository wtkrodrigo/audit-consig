import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB-SOLUÇÕES", layout="wide", page_icon="🛡️")

# --- CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- MENU ---
m = st.sidebar.selectbox("Módulo", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONÁRIO (Visual Mobile)
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta de Transparência")
    cpf_in = st.text_input("Seu CPF")
    cpf = "".join(filter(str.isdigit, cpf_in))
    if st.button("VERIFICAR") and cpf:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", cpf).order("data_processamento", desc=True).limit(1).execute()
        if r.data:
            d = r.data[0]; st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2 = st.columns(2)
            c1.metric("Folha RH", f"R$ {d['valor_rh']}")
            c2.metric("Banco", f"R$ {d['valor_banco']}")
            if d['diferenca'] == 0: st.info("✅ Valores Corretos")
            else: st.error(f"❌ Divergência: R$ {abs(d['diferenca'])}")
        else: st.warning("Dados não encontrados para este CPF.")

# 2. EMPRESA (Automação via Planilha)
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.link = q.data[0].get('link_planilha', "") # Puxa o link salvo
                st.rerun()
    else:
        st.subheader(f"Gestão Automática: {st.session_state.n}")
        if st.button("🔄 ATUALIZAR DADOS DA PLANILHA"):
            if st.session_state.link:
                try:
                    df = pd.read_csv(st.session_state.link)
                    df['dif'] = df['valor_rh'] - df['valor_banco']
                    
                    # Limpa e Publica no Supabase
                    sb.table("resultados_auditoria").delete().eq("nome_empresa", st.session_state.n).execute()
                    for _, r in df.iterrows():
                        pl = {"nome_empresa": st.session_state.n, "cpf": str(r['cpf']), "nome_funcionario": r['nome'], 
                              "valor_rh": float(r['valor_rh']), "valor_banco": float(r['valor_banco']), 
                              "diferenca": float(r['dif']), "status": "OK" if r['dif']==0 else "ERRO"}
                        sb.table("resultados_auditoria").insert(pl).execute()
                    st.success("Auditoria atualizada e disponível para os funcionários!")
                    st.dataframe(df)
                except: st.error("Erro ao ler planilha. Verifique o link CSV.")
            else: st.warning("Link da planilha não configurado pelo Admin.")

# 3. ADMIN (Cadastro com Link da Planilha)
elif m == "⚙️ Admin":
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            st.write("Novo Cliente")
            n, l, s = st.text_input("Empresa"), st.text_input("Login"), st.text_input("Senha", type='password')
            link = st.text_input("Link da Planilha (Publicado como CSV)")
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                sb.table("empresas").insert({"nome_empresa": n, "login": l, "senha": h(s), "data_expiracao": v, "link_planilha": link}).execute()
                st.success("Empresa cadastrada e integrada!")
