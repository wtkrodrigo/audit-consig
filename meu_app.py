import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; transition: 0.3s; }
    .stButton>button:hover { background: #d90429; color: white; }
    .dataframe { font-size: 12px !important; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nas Credenciais"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.markdown("### 🛡️ RRB PREMIUM")
m = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO (MANTIDO) ---
if m == "👤 Funcionário":
    st.subheader("🔎 Consulta do Colaborador")
    cpf_in = st.text_input("Digite seu CPF")
    c = "".join(filter(str.isdigit, cpf_in))
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
            col2.metric("Banco", d.get('banco_nome', 'N/A'))
            col3.metric("Contrato", ct)
            if tt > 0: st.progress(min(1.0, pg/tt))
        else: st.warning("CPF não localizado.")

# --- 2. MÓDULO EMPRESA (GESTÃO DETALHADA) ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        with st.columns([1,1.5,1])[1]:
            st.subheader("🔐 Login Corporativo")
            u_in = st.text_input("Usuário")
            p_in = st.text_input("Senha", type='password')
            if st.button("ACESSAR PAINEL"):
                q = sb.table("empresas").select("*").eq("login",u_in).execute()
                if q.data and h(p_in) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Login Inválido")
    else:
        h1, h2 = st.columns([4, 1])
        h1.subheader(f"🏢 Gestão de Auditoria: {st.session_state.n}")
        if h2.button("🔴 SAIR"):
            st.session_state.at = False; st.rerun()

        # ÁREA DE SINCRONIZAÇÃO COMPACTA
        with st.expander("📥 Importar e Sincronizar Folha", expanded=False):
            if st.button("🚀 EXECUTAR LANÇAMENTO MENSAL"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = pd.to_numeric(r['valor_rh'], errors='coerce')
                        vb = pd.to_numeric(r['valor_banco'], errors='coerce')
                        tp = pd.to_numeric(r['total_parcelas'], errors='coerce')
                        vr, vb = (float(x) if pd.notna(x) else 0.0 for x in [vr, vb])
                        tp = int(tp) if pd.notna(tp) else 0
                        
                        pld = {
                            "nome_empresa": st.session_state.n, "cpf": str(r['cpf']),
                            "nome_funcionario": str(r['nome']), "valor_rh": vr,
                            "valor_banco": vb, "diferenca": vr - vb,
                            "banco_nome": str(r.get('banco', 'N/A')),
                            "contrato_id": str(r.get('contrato', 'N/A')),
                            "parcelas_total": tp, "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_auditoria").insert(pld).execute()
                    st.success("✅ Folha processada e histórico atualizado!")
                except Exception as e: st.error(f"Erro: {e}")

        st.markdown("---")
        
        # BUSCA DE DADOS COM CÁLCULO DE PARCELAS PARA A TABELA
        st.write("📋 **Visão Geral de Contratos e Parcelas**")
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).order("data_processamento", desc=True).execute()
        
        if res.data:
            full_df = pd.DataFrame(res.data)
            
            # LÓGICA DE CONTABILIZAÇÃO PARA A TABELA
            # Para cada linha, contamos quantas vezes aquele contrato apareceu até aquela data
            vis_list = []
            for i, row in full_df.head(30).iterrows(): # Mostra os últimos 30 para ficar rápido
                # Conta no histórico total quantas vezes esse contrato apareceu
                p_pagas = len(full_df[full_df['contrato_id'] == row['contrato_id']])
                p_total = int(row['parcelas_total'])
                
                vis_list.append({
                    "Funcionário": row['nome_funcionario'],
                    "Banco": row['banco_nome'],
                    "ID Contrato": row['contrato_id'],
                    "V. RH": f"R$ {row['valor_rh']:.2f}",
                    "V. Banco": f"R$ {row['valor_banco']:.2f}",
                    "Dif.": f"R$ {row['diferenca']:.2f}",
                    "Pagas": f"{p_pagas}",
                    "Faltam": f"{max(0, p_total - p_pagas)}"
                })
            
            st.table(pd.DataFrame(vis_list)) # 'table' é mais elegante que 'dataframe' para relatórios fixos
        else:
            st.info("Aguardando primeiro lançamento.")

# --- 3. MÓDULO ADMIN (MANTIDO) ---
elif m == "⚙️ Admin":
    st.subheader("⚙️ Painel Master")
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            n = st.text_input("Empresa")
            lk = st.text_input("Link CSV")
            u_c = st.text_input("User")
            s_c = st.text_input("Pass", type='password')
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now()+timedelta(30)).strftime("%Y-%m-%d")
                di = {"nome_empresa": n, "login": u_c, "senha": h(s_c),
                      "data_expiracao": v, "link_planilha": lk}
                sb.table("empresas").insert(di).execute()
                st.success("Cliente Ativado!")
