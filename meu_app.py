import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"<div class='logo-container'><span style='font-size: 40px;'>🛡️</span><div class='logo-text'>RRB SOLUÇÕES | {titulo}</div></div>", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nos Secrets."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    c1, c2 = st.columns(2)
    cpf_in = c1.text_input("CPF (somente números)")
    dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
    tel_fim_in = st.text_input("Últimos 4 dígitos do celular", max_chars=4)
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            v_data = (str(dt_nasc_in) == str(d.get("data_nascimento", "")))
            v_fone = str(d.get("telefone", "")).endswith(tel_fim_in)
            if v_data and v_fone:
                st.success(f"Bem-vindo, {d['nome_funcionario']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                m2.metric("Banco", d.get('banco_nome', 'N/A'))
                stt = "✅ OK" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                m3.metric("Status", stt)
            else: st.error("Dados de validação não conferem.")
        else: st.warning("CPF não encontrado.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha'); st.rerun()
            else: st.error("Erro de login.")
    else:
        st.subheader(f"Empresa: {st.session_state.n}")
        eb1, eb2, _ = st.columns([1, 1, 2])
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_res = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        with eb1:
            if st.button("🔄 SINCRONIZAR"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0)
                        vb = float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                        pld = {
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
                            "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas', 0), 'coerce') or 0),
                            "data_nascimento": str(r.get('data_nascimento', '')),
                            "telefone": "".join(filter(str.isdigit, str(r.get('telefone', "")))),
                            "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_auditoria").upsert(pld).execute()
                    st.success("Sincronizado!"); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

        with eb2:
            if not df_res.empty:
                st.download_button("📥 EXPORTAR", df_res.to_csv(index=False).encode('utf-8'), "auditoria.csv", "text/csv")
        
        st.write("---")
        busca = st.text_input("🔍 Pesquisar")
        if not df_res.empty:
            if busca:
                df_res = df_res[df_res['nome_funcionario'].str.contains(busca, case=False, na=False) | df_res['cpf'].str.contains(busca, na=False)]
            st.dataframe(df_res, use_container_width=True, hide_index=True)

        if st.sidebar.button("🚪 Sair"):
            st.session_state.at = False; st.rerun()

# --- MÓDULO ADMIN ---
elif menu == "⚙️ Admin Master":
    render_header("Admin Master")
    if st.sidebar.text_input("Master Key", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            f1, f2 = st.columns(2)
            rz = f1.text_input("Razão Social")
            cj = f2.text_input("CNPJ")
            lo, se = f1.text_input("Login"), f2.text_input("Senha", type='password')
            lk = st.text_input("Link CSV")
            if st.form_submit_button("✅ SALVAR"):
                if rz and lo and se:
                    dt = {"nome_empresa": rz, "cnpj": cj, "login": lo, "senha": h(se), "link_planilha": lk}
                    sb.table("empresas").insert(dt).execute()
                    st.success("Salvo!"); st.rerun()
        
        lst = sb.table("empresas").select("nome_empresa, cnpj").execute()
        if lst.data: st.table(pd.DataFrame(lst.data))
