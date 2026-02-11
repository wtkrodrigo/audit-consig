import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Transparência", layout="wide", page_icon="🛡️")

# --- DESIGN MODERNO (CSS SEGURO) ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card-resumo { background: white; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; margin-top: 20px; }
    .trust-badge { padding: 8px 15px; background: #002D62; color: white; border-radius: 8px; font-weight: bold; display: inline-block; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Erro de conexão com o Banco de Dados.")
    st.stop()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- NAVEGAÇÃO ---
menu = ["Portal do Funcionário", "Portal da Empresa", "Administração RRB"]
escolha = st.sidebar.selectbox("Selecione o Portal", menu)

# ---------------------------------------------------------
# 1. PORTAL DO FUNCIONÁRIO (MODERNO E SEGURO)
# ---------------------------------------------------------
if escolha == "Portal do Funcionário":
    st.markdown('<div class="trust-badge">🛡️ AUDITORIA RRB-SOLUÇÕES</div>', unsafe_allow_html=True)
    st.title("Transparência do Colaborador")
    st.write("Consulte seus descontos de forma segura e independente.")

    cpf_input = st.text_input("Seu CPF", placeholder="000.000.000-00")
    cpf_busca = "".join(filter(str.isdigit, cpf_input))

    if st.button("Consultar Meus Dados"):
        if cpf_busca:
            res = supabase.table("resultados_auditoria").select("*").eq("cpf", cpf_busca).order("data_processamento", desc=True).limit(1).execute()
            
            if res.data:
                d = res.data[0]
                st.markdown(f"### Olá, **{d['nome_funcionario']}**")
                
                st.markdown('<div class="card-resumo">', unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Declarado RH", f"R$ {d['valor_rh']}")
                m2.metric("Base Banco", f"R$ {d['valor_banco']}")
                m3.metric("Diferença", f"R$ {d['diferenca']}", delta=-d['diferenca'] if d['diferenca'] != 0 else None)
                
                st.write("---")
                
                if d['status'] == "✅ OK":
                    st.success("✅ CONFORMIDADE TOTAL: Seus descontos estão corretos.")
                    st.progress(100)
                else:
                    st.error(f"⚠️ DIVERGÊNCIA IDENTIFICADA: Foi encontrada uma diferença de R$ {abs(d['diferenca'])}. Procure o seu RH.")
                    st.progress(50)
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Dados não localizados. Verifique o CPF ou se a empresa já finalizou a auditoria.")
        else:
            st.warning("Informe o CPF para consultar.")

# ---------------------------------------------------------
# 2. PORTAL DA EMPRESA
# ---------------------------------------------------------
elif escolha == "Portal da Empresa":
    if 'emp_auth' not in st.session_state: st.session_state['emp_auth'] = False

    if not st.session_state['emp_auth']:
        st.subheader("🔐 Login Empresa")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("Acessar"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data and check_hashes(p, q.data[0]['senha']):
                st.session_state['emp_auth'] = True
                st.session_state['emp_nome'] = q.data[0]['nome_empresa']
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        st.subheader(f"📊 Auditoria - {st.session_state['emp_nome']}")
        f1 = st.file_uploader("Folha RH", type=['csv'])
        f2 = st.file_uploader("Base Banco", type=['csv'])
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devio_banco'] if 'valor_devio_banco' in res.columns else res['valor_descontado_rh'] # Fallback
            res['Status'] = res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")
            st.dataframe(res)
            if st.button("🚀 LIBERAR PARA FUNCIONÁRIOS"):
                for _, row in res.iterrows():
                    p = {"nome_empresa": st.session_state['emp_nome'], "cpf": str(row['cpf']), "nome_funcionario": row['nome'], "valor_rh": float(row['valor_descontado_rh']), "valor_banco": float(row.get('valor_devio_banco', 0)), "diferenca": float(row['Diferença']), "status": row['Status']}
                    supabase.table("resultados_auditoria").insert(p).execute()
                st.success("Publicado!")

# ---------------------------------------------------------
# 3. ADMINISTRAÇÃO
# ---------------------------------------------------------
elif escolha == "Administração RRB":
    st.subheader("🛠️ Gestão Master")
    sm = st.text_input("Senha Master", type='password')
    if sm == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            n = st.text_input("Empresa")
            l = st.text_input("Login")
            s = st.text_input("Senha", type='password')
            if st.form_submit_button("CADASTRAR"):
                exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                d = {"nome_empresa": n, "login": l, "senha": make_hashes(s), "data_expiracao": exp}
                supabase.
