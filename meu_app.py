import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB", layout="wide")

st.markdown("""<style>
    .stMetric { background: white; padding: 15px; 
    border-radius: 10px; border-left: 5px solid #002D62; }
</style>""", unsafe_allow_html=True)

# --- DB ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p):
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
m = st.sidebar.selectbox("Menu", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONARIO
if m == "👤 Func":
    st.subheader("🔎 Status do Empréstimo")
    c_in = st.text_input("CPF (apenas números)")
    c = "".join(filter(str.isdigit, c_in))
    if st.button("VERIFICAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pagas = len(hist)
            total = int(d.get('parcelas_total', 0))
            
            st.info(f"🏦 {d.get('banco_nome')} | 📄 Contrato: {ct}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Pagas", f"{pagas} de {total}")
            c2.metric("Restantes", f"{max(0, total - pagas)}")
            c3.metric("Status", "Em dia" if d['diferenca']==0 else "Erro")
            
            if total > 0:
                st.progress(min(1.0, pagas/total))
        else:
            st.warning("Não encontrado.")

# 2. EMPRESA
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_in = st.text_input("Login")
        p_in = st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
    else:
        c_t, c_s = st.columns([4, 1])
        c_t.subheader(f"Painel: {st.session_state.n}")
        if c_s.button("🔴 SAIR"):
            st.session_state.at = False
            st.rerun()
            
        if st.button("🔄 LANÇAR PAGAMENTO MENSAL"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                for _, r in df.iterrows():
                    v_rh, v_ba = float(r['valor_rh']), float(r['valor_banco'])
                    pld = {
                        "nome_empresa": st.session_state.n,
                        "cpf": str(r['cpf']),
                        "nome_funcionario": r['nome'],
                        "valor_rh": v_rh, "valor_banco": v_ba,
                        "diferenca": v_rh - v_ba,
                        "banco_nome": str(r['banco']),
                        "contrato_id": str(r['contrato']),
                        "parcelas_total": int(r['total_parcelas']),
                        "data_processamento": datetime.now().isoformat()
                    }
                    sb.table("resultados_auditoria").insert(pld).execute()
                st.success("✅ Lançamento Concluído!")
            except Exception as e: st.error(f"Erro: {e}")

# 3. ADMIN
elif m == "⚙️ Admin":
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad_rrb"):
            st.write("Novo Cliente")
            n = st.text_input("Empresa")
            lk = st.text_input("Link CSV")
            u_c = st.text_input("User")
            s_c = st.text_input("Pass", type='password')
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now()+timedelta(30)).strftime("%Y-%m-%d")
                di = {"nome_empresa": n, "login": u_c, "senha": h(s_c),
                      "data_expiracao": v, "link_planilha": lk}
                sb.table("empresas").insert(di).execute()
                st.success(f"Ativo até {v}")
