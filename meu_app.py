import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Ecossistema", layout="wide", page_icon="🛡️")

# --- DESIGN ---
st.markdown("<style>.main { background-color: #f0f2f6; } .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; background-color: #002D62; color: white; }</style>", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Erro nos Secrets do Supabase.")
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
    st.header("👤 Área do Colaborador")
    st.info("Consulte a transparência dos seus descontos consignados.")
    
    cpf_busca = st.text_input("Digite seu CPF (apenas números)", placeholder="000.000.000-00")
    
    if st.button("VERIFICAR MEU DESCONTO"):
        if cpf_busca:
            # Busca o resultado mais recente para aquele CPF
            res = supabase.table("resultados_auditoria").select("*").eq("cpf", cpf_busca).order("data_processamento", desc=True).limit(1).execute()
            
            if res.data:
                d = res.data[0]
                st.success(f"Olá, {d['nome_funcionario']}! Dados localizados.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Valor em Folha (RH)", f"R$ {d['valor_rh']}")
                c2.metric("Valor no Banco", f"R$ {d['valor_banco']}")
                
                # Se houver diferença, mostra em vermelho
                delta_color = "inverse" if d['diferenca'] != 0 else "normal"
                c3.metric("Divergência", f"R$ {d['diferenca']}", delta=d['diferenca'], delta_color=delta_color)
                
                if d['status'] == "✅ OK":
                    st.balloons()
                    st.success("🎯 Tudo certo! Seu desconto está correto.")
                else:
                    st.error("⚠️ Atenção: Foi encontrada uma divergência no seu desconto. Procure o RH.")
            else:
                st.warning("CPF não encontrado. Certifique-se de que a empresa já realizou a auditoria deste mês.")

# ---------------------------------------------------------
# 2. PORTAL DA EMPRESA
# ---------------------------------------------------------
elif escolha == "Portal da Empresa":
    if 'emp_auth' not in st.session_state: st.session_state['emp_auth'] = False

    if not st.session_state['emp_auth']:
        st.subheader("🔐 Login Corporativo")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = supabase.table("empresas").select("*").eq("login", u).execute()
            if q.data:
                d = q.data[0]
                exp = datetime.strptime(d['data_expiracao'], "%Y-%m-%d")
                if datetime.now() > exp:
                    st.error("Assinatura Expirada.")
                elif check_hashes(p, d['senha']):
                    st.session_state['emp_auth'] = True
                    st.session_state['emp_nome'] = d['nome_empresa']
                    st.rerun()
            else: st.error("Login inválido.")
    
    else:
        st.subheader(f"📊 Painel de Auditoria - {st.session_state['emp_nome']}")
        f1 = st.file_uploader("Base RH (CSV)", type=['csv'])
        f2 = st.file_uploader("Base Banco (CSV)", type=['csv'])

        if f1 and f2:
            df1 = pd.read_csv(f1)
            df2 = pd.read_csv(f2)
            res = pd.merge(df1, df2, on='cpf', suffixes=('_RH', '_BANCO'))
            
            res['Diferença'] = res['valor_descontado_rh'] - res['valor_devido_banco']
            res['Status'] = res['Diferença'].apply(lambda x: "❌ DIVERGENTE" if x != 0 else "✅ OK")
            
            st.dataframe(res, use_container_width=True)

            if st.button("🚀 FINALIZAR E LIBERAR PARA FUNCIONÁRIOS"):
                with st.spinner("Integrando dados..."):
                    for _, row in res.iterrows():
                        payload = {
                            "nome_empresa": st.session_state['emp_nome'],
                            "cpf": str(row['cpf']),
                            "nome_funcionario": row['nome'],
                            "valor_rh": float(row['valor_descontado_rh']),
                            "valor_banco": float(row['valor_devido_banco']),
                            "diferenca": float(row['Diferença']),
                            "status": row['Status']
                        }
                        supabase.table("resultados_auditoria").insert(payload).execute()
                    st.success("✅ Auditoria finalizada! Os funcionários já podem consultar seus CPFs.")

# ---------------------------------------------------------
# 3. ADMINISTRAÇÃO (CADASTRO)
# ---------------------------------------------------------
elif escolha == "Administração RRB":
    st.subheader("🛠️ Gestão Master")
    sm = st.text_input("Senha Master", type='password')
    if sm == st.secrets.get("SENHA_MASTER", "admin"):
        with st.form("cad"):
            nome = st.text_input("Nome Empresa")
            login = st.text_input("Login")
            senha = st.text_input("Senha", type='password')
            plano = st.selectbox("Plano", ["Bronze", "Prata", "Ouro"])
            if st.form_submit_button("CADASTRAR"):
                # Lógica de expiração simplificada para o exemplo
                exp = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                dados = {"nome_empresa": nome, "login": login, "senha": make_hashes(senha), "data_expiracao": exp, "plano_mensal": plano}
                supabase.table("empresas").insert(dados).execute()
                st.success("Empresa Cadastrada!")
