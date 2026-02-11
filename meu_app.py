import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #002D62; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 5px; height: 2.5em; font-weight: 600; }
    .compact-table { font-size: 0.9rem !important; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nas Credenciais"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.title("🛡️ RRB Admin")
m = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    st.subheader("🔎 Painel do Colaborador")
    with st.container():
        c_in = st.text_input("CPF para consulta")
        c = "".join(filter(str.isdigit, c_in))
        if st.button("VERIFICAR") and c:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
            if r.data:
                d = r.data[-1]
                st.success(f"Olá, {d['nome_funcionario']}")
                ct = d.get('contrato_id')
                hist = [x for x in r.data if x.get('contrato_id') == ct]
                pg, tt = len(hist), int(d.get('parcelas_total', 0))
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Parcelas", f"{pg}/{tt}")
                col2.metric("Pendente", f"R$ {d['diferenca']:.2f}")
                col3.metric("Status", "✅ OK" if d['diferenca']==0 else "⚠️ Alerta")
                
                if tt > 0: st.progress(min(1.0, pg/tt))
            else: st.warning("Dados não localizados.")

# --- 2. MÓDULO EMPRESA (COMPACTO) ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        with st.columns([1,2,1])[1]:
            st.subheader("🔐 Login Empresa")
            u_in = st.text_input("Usuário")
            p_in = st.text_input("Senha", type='password')
            if st.button("ACESSAR"):
                q = sb.table("empresas").select("*").eq("login",u_in).execute()
                if q.data and h(p_in) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Erro de login")
    else:
        # Layout Compacto
        h1, h2 = st.columns([3, 1])
        h1.subheader(f"🏢 {st.session_state.n}")
        if h2.button("🔴 SAIR"):
            st.session_state.at = False; st.rerun()

        # Dashboard de Sincronização
        with st.expander("🔄 Sincronização de Dados", expanded=True):
            c1, c2 = st.columns([2, 1])
            c1.write("Clique para processar a folha de pagamento atual.")
            if c2.button("EXECUTAR AGORA"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = pd.to_numeric(r['valor_rh'], errors='coerce')
                        vb = pd.to_numeric(r['valor_banco'], errors='coerce')
                        tp = pd.to_numeric(r['total_parcelas'], errors='coerce')
                        vr, vb = (0.0 if pd.isna(x) else float(x) for x in [vr, vb])
                        tp = 0 if pd.isna(tp) else int(tp)
                        
                        pld = {
                            "nome_empresa": st.session_state.n,
                            "cpf": str(r['cpf']), "nome_funcionario": str(r['nome']),
                            "valor_rh": vr, "valor_banco": vb, "diferenca": vr - vb,
                            "banco_nome": str(r.get('banco', 'N/A')),
                            "contrato_id": str(r.get('contrato', 'N/A')),
                            "parcelas_total": tp,
                            "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_auditoria").insert(pld).execute()
                    st.success("✅ Processado com sucesso!")
                except Exception as e: st.error(f"Erro: {e}")

        # Tabela Compacta de Histórico
        st.write("📋 **Últimos Registros Auditados**")
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).order(
            "data_processamento", desc=True).limit(15).execute()
        
        if res.data:
            dv = pd.DataFrame(res.data)
            # Criando coluna visual de parcelas na tabela
            dv['Progresso'] = dv['parcelas_total'].astype(str) + " tot."
            st.dataframe(dv[['nome_funcionario', 'valor_rh', 'valor_banco', 
                             'diferenca', 'Progresso']], use_container_width=True)

# --- 3. MÓDULO ADMIN ---
elif m == "⚙️ Admin":
    st.subheader("⚙️ Configurações Master")
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Empresa")
            lk = c1.text_input("CSV Link")
            u_c = c2.text_input("User")
            s_c = c2.text_input("Pass", type='password')
            if st.form_submit_button("SALVAR CLIENTE"):
                v = (datetime.now()+timedelta(30)).strftime("%Y-%m-%d")
                di = {"nome_empresa": n, "login": u_c, "senha": h(s_c),
                      "data_expiracao": v, "link_planilha": lk}
                sb.table("empresas").insert(di).execute()
                st.success("Cliente Registado!")
