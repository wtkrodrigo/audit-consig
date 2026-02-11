import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB", layout="wide")

# --- CSS MODERNO (DESIGN PREMIUM) ---
st.markdown("""<style>
    .main { background-color: #f0f2f6; }
    .stMetric { background: white; padding: 20px; 
    border-radius: 12px; border-left: 6px solid #002D62;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 8px;
    background: #002D62; color: white; height: 3em; }
</style>""", unsafe_allow_html=True)

# --- DB ---
try:
    u = st.secrets["SUPABASE_URL"]
    k = st.secrets["SUPABASE_KEY"]
    sb = create_client(u, k)
except:
    st.error("Erro Secrets"); st.stop()

def h(p):
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- HEADER ---
st.title("🛡️ RRB SOLUÇÕES")
st.caption("Auditoria Inteligente de Consignados")

# --- NAVEGAÇÃO ---
m = st.sidebar.radio("MENU PRINCIPAL", 
    ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    st.subheader("🔎 Minha Auditoria")
    cpf_in = st.text_input("CPF (somente números)")
    c = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("VERIFICAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq(
            "cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Bem-vindo, {d['nome_funcionario']}")
            
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg, tt = len(hist), int(d.get('parcelas_total', 0))
            
            st.info(f"🏦 {d.get('banco_nome')} | 📄 CTR: {ct}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Pagas", f"{pg} de {tt}")
            c2.metric("Restam", f"{max(0, tt - pg)}")
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Erro")
            
            if tt > 0:
                st.progress(min(1.0, pg/tt))
        else:
            st.warning("CPF não localizado.")

# --- 2. MÓDULO EMPRESA ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state:
        st.session_state.at = False
        
    if not st.session_state.at:
        st.subheader("🔐 Acesso Restrito - Empresa")
        u_in = st.text_input("Login")
        p_in = st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq(
                "login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else:
                st.error("Dados inválidos")
    else:
        # Área Logada
        st.subheader(f"🏢 Gestão: {st.session_state.n}")
        if st.sidebar.button("🔴 SAIR"):
            st.session_state.at = False
            st.rerun()
            
        if st.button("🔄 SINCRONIZAR FOLHA DO MÊS"):
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
                        "cpf": str(r['cpf']),
                        "nome_funcionario": str(r['nome']),
                        "valor_rh": vr, "valor_banco": vb,
                        "diferenca": vr - vb,
                        "banco_nome": str(r.get('banco', 'N/A')),
                        "contrato_id": str(r.get('contrato', 'N/A')),
                        "parcelas_total": tp
                    }
                    sb.table("resultados_auditoria").insert(pld).execute()
                st.success("✅ Sincronizado!")
            except Exception as e:
                st.error(f"Erro: {e}")

        st.markdown("---")
        # Visualização da Tabela
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).order(
            "data_processamento", desc=True).limit(20).execute()
        if res.data:
            st.write("📊 Últimos Lançamentos")
            st.dataframe(pd.DataFrame(res.data)[['nome_funcionario', 
                'valor_rh', 'valor_banco', 'diferenca']])

# --- 3. MÓDULO ADMIN ---
elif m == "⚙️ Admin":
    st.subheader("⚙️ Painel de Controle RRB")
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            st.write("Novo Cliente")
            n = st.text_input("Nome da Empresa")
            lk = st.text_input("Link CSV")
            u_c = st.text_input("User")
            s_c = st.text_input("Senha", type='password')
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now()+timedelta(30)).strftime("%Y-%m-%d")
                di = {"nome_empresa": n, "login": u_c, 
                      "senha": h(s_c), "data_expiracao": v, 
                      "link_planilha": lk}
                sb.table("empresas").insert(di).execute()
                st.success(f"Ativado até {v}")
