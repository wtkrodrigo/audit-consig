import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

# Estilos CSS
st.markdown("""<style>
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-text { font-size: 32px; font-weight: bold; color: #002D62; }
    .admin-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO SUPABASE ---
try:
    su = st.secrets["SUPABASE_URL"]
    sk = st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except Exception as e:
    st.error("Erro nos Secrets do Supabase.")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.title("🛡️ RRB SOLUÇÕES")
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    st.markdown("<div class='logo-text'>Portal do Funcionário</div>", unsafe_allow_html=True)
    st.write("---")
    cpf_raw = st.text_input("Digite seu CPF")
    cpf_clean = "".join(filter(str.isdigit, cpf_raw))
    
    if st.button("BUSCAR") and cpf_clean:
        res = sb.table("resultados_auditoria").select("*").eq("cpf", cpf_clean).execute()
        if res.data:
            d = res.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            c3.metric("Status", "✅ OK" if d.get('diferenca', 0) == 0 else "⚠️ Divergência")
        else:
            st.warning("CPF não localizado.")

# --- 2. MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    st.markdown("<div class='logo-text'>Painel da Empresa</div>", unsafe_allow_html=True)
    st.write("---")
    
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u_in = st.text_input("Usuário Corporativo")
        p_in = st.text_input("Senha Corporativa", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else:
                st.error("Login ou senha inválidos.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.sidebar.button("LOGOUT"):
            st.session_state.at = False
            st.rerun()

        if st.button("🔄 SINCRONIZAR PLANILHA AGORA"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                for _, r in df.iterrows():
                    vr, vb = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0), float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                    payload = {
                        "nome_empresa": st.session_state.n,
                        "cpf": "".join(filter(str.isdigit, str(r['cpf']))),
                        "nome_funcionario": str(r['nome']),
                        "valor_rh": vr,
                        "valor_banco": vb,
                        "valor_emprestimo": float(pd.to_numeric(r.get('valor_emprestimo', 0), 'coerce') or 0),
                        "diferenca": round(vr - vb, 2),
                        "banco_nome": str(r.get('banco', 'N/A')),
                        "contrato_id": str(r.get('contrato', 'N/A')),
                        "parcelas_total": int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0),
                        "data_processamento": datetime.now().isoformat()
                    }
                    sb.table("resultados_auditoria").upsert(payload, on_conflict="cpf,contrato_id").execute()
                st.success("Sincronização concluída!")
            except Exception as e: st.error(f"Erro: {e}")

        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st
