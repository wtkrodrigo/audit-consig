import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .logo-text { font-size: 26px; font-weight: bold; color: #002D62; margin-bottom: 20px; }
</style>""", unsafe_allow_html=True)

def logo():
    st.markdown("<div class='logo-text'>🛡️ RRB SOLUÇÕES AUDITORIA</div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO SUPABASE ---
try:
    su = st.secrets["SUPABASE_URL"]
    sk = st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except Exception as e:
    st.error("Erro nas credenciais do Supabase.")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.title("MENU PRINCIPAL")
menu = st.sidebar.radio("Ir para:", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- MÓDULO 1: FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    logo()
    cpf_raw = st.text_input("Informe seu CPF (apenas números)")
    cpf_clean = "".join(filter(str.isdigit, cpf_raw))
    
    if st.button("CONSULTAR") and cpf_clean:
        res = sb.table("resultados_auditoria").select("*").eq("cpf", cpf_clean).execute()
        if res.data:
            dados = res.data[-1]
            st.success(f"Olá, {dados['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade (RH)", f"R$ {dados.get('valor_rh', 0):,.2f}")
            c2.metric("Banco", dados.get('banco_nome', 'N/A'))
            c3.metric("Status", "✅ OK" if dados.get('diferenca', 0) == 0 else "❌ Divergência")
        else:
            st.warning("CPF não localizado.")

# --- MÓDULO 2: EMPRESA ---
elif menu == "🏢 Empresa":
    logo()
    if 'autenticado' not in st.session_state: st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        u_in = st.text_input("Usuário Empresa")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            query = sb.table("empresas").select("*").eq("login", u_in).execute()
            if query.data and h(p_in) == query.data[0]['senha']:
                st.session_state.autenticado = True
                st.session_state.nome_emp = query.data[0]['nome_empresa']
                st.session_state.url_planilha = query.data[0].get('link_planilha')
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    else:
        st.subheader(f"Painel: {st.session_state.nome_emp}")
        if st.sidebar.button("SAIR"): 
            st.session_state.autenticado = False
            st.rerun()
        
        if st.button("🔄 SINCRONIZAR PLANILHA"):
            try:
                df = pd.read_csv(st.session_state.url_planilha)
                df.columns = df.columns.str.strip().str.lower()
                for _, row in df.iterrows():
                    v_rh = float(pd.to_numeric(row.get('valor_rh', 0), 'coerce') or 0)
                    v_bc = float(pd.to_numeric(row.get('valor_banco', 0), 'coerce') or 0)
                    cpf_limpo = "".join(filter(str.isdigit, str(row['cpf'])))
                    
                    payload = {
                        "nome_empresa": st.session_state.nome_emp,
                        "cpf": cpf_limpo,
                        "nome_funcionario": str(row['nome']),
                        "valor_rh": v_rh,
                        "valor_banco": v_bc,
                        "valor_emprestimo": float(pd.to_numeric(row.get('valor_emprestimo', 0), 'coerce') or 0),
                        "diferenca": round(v_rh - v_bc, 2),
                        "banco_nome": str(row.get('banco', 'N/A')),
                        "contrato_id": str(row.get('contrato', 'N/A')),
                        "parcelas_total": int(pd.to_numeric(row.get('total_parcelas', 0), 'coerce') or 0),
                        "data_processamento": datetime.now().isoformat()
                    }
                    # O comando upsert abaixo evita duplicatas usando o CPF e o Contrato como chave
                    sb.table("resultados_auditoria").upsert(payload, on_conflict="cpf,contrato_id").execute()
                st.success("Dados sincronizados com sucesso!")
            except Exception as e: 
                st.error(f"Erro na sincronização: {e}")

        # Visualização básica dos dados processados
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.nome_emp).execute()
        if res_db.data:
            st.dataframe(pd.DataFrame(res_db.data), use_container_width=True)

# --- MÓDULO 3: ADMIN ---
elif menu == "⚙️ Admin":
    logo()
    senha_mestre = st.secrets.get("SENHA_MASTER", "RRB123")
    check_pass = st.text_input("Chave Mestra", type='password')
    
    if check_pass == senha_mestre:
        st.success("Acesso Liberado")
        with st.form("cadastro_empresa_form"):
            c1, c2 = st.columns(2)
            razao = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            login_emp = c1.text_input("Login de Acesso")
            senha_emp = c2.text_input("Senha de Acesso", type='password')
            link = st.text_input("Link CSV da Planilha")
            
            if st.form_submit_button("SALVAR EMPRESA"):
                if razao and login_emp and senha_emp:
                    dados_emp = {
                        "nome_empresa": razao,
                        "cnpj": cnpj,
                        "login": login_emp,
                        "senha": h(senha_emp),
                        "link_planilha": link,
                        "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    try:
                        sb.table("empresas").insert(dados_emp).execute()
                        st.success(f"Empresa {razao} cadastrada!")
                    except Exception as e: 
                        st.error(f"Erro ao salvar: {e}")
