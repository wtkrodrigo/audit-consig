import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd; }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>""", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Erro nos Secrets do Supabase."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    cpf_in = st.text_input("Digite seu CPF (somente números)")
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Bem-vindo, {d['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
            c3.metric("Status", status)
            
            with st.expander("🔍 Detalhamento e Dados Cadastrais"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**Dados do Contrato**")
                    st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                    st.write(f"**Contrato:** {d.get('contrato_id', 'N/A')}")
                    pp, pt = d.get('parcelas_pagas', 0), d.get('parcelas_total', 0)
                    st.write(f"**Parcelas:** {pp} de {pt}")
                    if pt > 0: st.progress(min(pp / pt, 1.0))
                with col_b:
                    st.write("**Dados Cadastrais**")
                    st.write(f"**Nascimento:** {d.get('data_nascimento', 'N/A')}")
                    st.write(f"**Telefone:** {d.get('telefone', 'N/A')}")
        else:
            st.warning("CPF não encontrado.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u = st.text_input("Usuário"); p = st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha'); st.rerun()
            else: st.error("Erro de login.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.button("🔄 SINCRONIZAR AGORA"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                for _, r in df.iterrows():
                    vr, vb = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0), float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                    payload = {
                        "nome_empresa": st.session_state.n, "cpf": "".join(filter(str.isdigit, str(r['cpf']))),
                        "nome_funcionario": str(r['nome']), "valor_rh": vr, "valor_banco": vb,
                        "valor_emprestimo": float(pd.to_numeric(r.get('valor_emprestimo', 0), 'coerce') or 0),
                        "diferenca": round(vr - vb, 2), "banco_nome": str(r.get('banco', 'N/A')),
                        "contrato_id": str(r.get('contrato', 'N/A')),
                        "parcelas_total": int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0),
                        "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas', 0), 'coerce') or 0),
                        "data_nascimento": str(r.get('data_nascimento', '')),
                        "telefone": "".join(filter(str.isdigit, str(r.get('telefone', "")))),
                        "data_processamento": datetime.now().isoformat()
                    }
                    sb.table("resultados_auditoria").upsert(payload).execute()
                st.success("Sincronizado!")
            except Exception as e: st.error(f"Erro: {e}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        if res_db.data: st.dataframe(pd.DataFrame(res_db.data), use_container_width=True)

# --- MÓDULO ADMIN ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            st.subheader("📝 Cadastrar Empresa")
            c1, c2 = st.columns(2); rz = c1.text_input("Razão"); cj = c2.text_input("CNPJ")
            lo = c1.text_input("Login"); se = c2.text_input("Senha", type='password'); lk = st.text_input("Link CSV")
            if st.form_submit_button("✅ SALVAR"):
                dt = {"nome_empresa": rz, "cnpj": cj, "login": lo, "senha": h(se), "link_planilha": lk}
                sb.table("empresas").insert(dt).execute(); st.success("Salvo!")
