import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Ecossistema", layout="wide", page_icon="🛡️")

# --- DESIGN ---
st.markdown("<style>.main { background-color: #f8f9fa; } .stMetric { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); } .card-resumo { background: white; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; }</style>", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

# --- NAVEGAÇÃO ---
menu = ["Portal do Funcionário", "Portal da Empresa", "Administração RRB"]
escolha = st.sidebar.selectbox("Selecione o Portal", menu)

# ---------------------------------------------------------
# 1. PORTAL DO FUNCIONÁRIO
# ---------------------------------------------------------
if escolha == "Portal do Funcionário":
    st.title("🛡️ Transparência do Colaborador")
    st.write("Consulte a integridade dos seus descontos consignados.")
    
    cpf_input = st.text_input("Seu CPF (apenas números)")
    cpf_busca = "".join(filter(str.isdigit, cpf_input))
    
    if st.button("Verificar Meus Dados"):
        if cpf_busca:
            res = supabase.table("resultados_auditoria").select("*").eq("cpf", cpf_busca).order("data_processamento", desc=True).limit(1).execute()
            if res.data:
                d = res.data[0]
                st.markdown(f"### Olá, **{d['nome_funcionario']}**")
                st.markdown('<div class="card-resumo">', unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Valor em Folha", f"R$ {d['valor_rh']}")
                m2.metric("Valor no Banco", f"R$ {d['valor_banco']}")
                m3.metric("Diferença", f"R$ {d['diferenca']}", delta=-d['diferenca'] if d['diferenca'] != 0 else None)
                
                if d['status'] == "✅ OK":
                    st.success("✅ CONFORMIDADE: Seus descontos estão corretos.")
                else:
                    st.error(f"⚠️ DIVERGÊNCIA: Foi encontrada uma diferença de R$ {abs(d['diferenca'])}. Procure seu RH.")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Dados não encontrados para este CPF.")
        else:
            st.warning("Por favor, digite seu CPF.")

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
            else: st.error("Acesso Negado.")
    else:
        st.subheader(f"📊 Auditoria - {st.session_state['emp_nome']}")
        f1 = st.file_uploader("Base RH", type=['csv'])
        f2 = st.file_uploader("Base Banco", type=['csv'])
        if f1 and f2:
            df1, df2 = pd.read_csv(f1), pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")
            st.dataframe(res)
            if st.button("🚀 PUBLICAR PARA FUNCIONÁRIOS"):
                for _, r in res.iterrows():
                    payload = {"nome_empresa": st.session_state['emp_nome'], "cpf": str(r['cpf']), "nome_funcionario": r['nome'], "valor_rh": float(r['valor_descontado_rh']), "valor_banco": float(r['valor_devido_banco']), "diferenca": float(r['Diferença']), "status": r['Status']}
                    supabase.table("resultados_auditoria").insert(payload).execute()
                st.success("Dados publicados com sucesso!")

# ---------------------------------------------------------
# 3. ADMINISTRAÇÃO RRB
# ---------------------------------------------------------
elif escolha == "Administração RRB":
    st.subheader("🛠️ Gestão Master")
    sm = st.text_input("Senha Master", type='password')
    if sm == st.secrets.get("SENHA_MASTER"):
        with st.form("cad_emp"):
            nome = st.text_input("Nome da Empresa")
            user = st.text_input("Login")
            senha = st.text_input("Senha", type='password')
            plano = st.
        
