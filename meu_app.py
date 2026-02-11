import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E CONEXÃO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

try:
    U, K = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(U, K)
except:
    st.error("Erro nos Secrets."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()
TA, TE = "resultados_auditoria", "empresas"

# --- ABA FUNCIONÁRIO ---
def aba_funcionario():
    st.markdown("### 🛡️ PORTAL DO FUNCIONÁRIO")
    c1, c2 = st.columns(2)
    cpf = c1.text_input("CPF (apenas números)")
    dt = c2.date_input("Nascimento", min_value=datetime(1940,1,1), format="DD/MM/YYYY")
    tel = st.text_input("Últimos 4 dígitos do celular", max_chars=4)
    cf = "".join(filter(str.isdigit, cpf))
    if st.button("CONSULTAR") and cf:
        r = sb.table(TA).select("*").eq("cpf", cf).execute()
        if r.data:
            d = r.data[-1]
            v_dt = str(dt) == str(d.get("data_nascimento",""))
            v_tl = str(d.get("telefone","")).endswith(tel)
            if v_dt and v_tl:
                st.success(f"Olá, {d['nome_funcionario']}")
                cl1, cl2, cl3 = st.columns(3)
                cl1.metric("Mensalidade", f"R$ {d.get('valor_rh',0):,.2f}")
                cl2.metric("Banco", d.get('banco_nome','N/A'))
                stt = "✅ CONFORME" if d.get('diferenca',0)==0 else "⚠️ DIVERGÊNCIA"
                cl3.metric("Status", stt)
                with st.expander("Detalhes"):
                    pp, pt = int(d.get("parcelas_pagas",0)), int(d.get("parcelas_total",0))
                    st.write(f"Contrato: {d.get('contrato_id','N/A')}"); st.write(f"Parcelas: {pp}/{pt}")
                    if pt > 0: st.progress(min(pp/pt, 1.0))
            else: st.error("Dados incorretos.")
        else: st.warning("CPF não encontrado.")

# --- ABA EMPRESA ---
def aba_empresa():
    st.markdown("### 🏢 PAINEL DA EMPRESA")
    if "at" not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u, p = st.text_input("Login"), st.text_input("Senha", type="password")
        if st.button("ENTRAR"):
            q = sb.table(TE).select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]["senha"]:
                st.session_state.at, st.session_state.n = True, q.data[0]["nome_empresa"]
                st.session_state.lk = q.data[0].get("link_planilha"); st.rerun()
            else: st.error("Login inválido.")
    else:
        st.subheader(f"Empresa: {st.session_state.n}")
        if st.button("🔄 SINCRONIZAR"):
            try:
                with st.spinner("Lendo..."):
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, row in df.iterrows():
                        vr, vb = float(row.get("valor_rh",0)), float(row.get("valor_banco",0))
                        payload = {
                            "nome_empresa": st.session_state.n, "cpf": "".join(filter(str.isdigit, str(row["cpf"]))),
                            "nome_funcionario": str(row["nome"]), "valor_rh": vr, "valor_banco": vb,
                            "diferenca": round(vr - vb, 2), "banco_nome": str(row.get("banco", "N/A")),
                            "contrato_id": str(row.get("contrato", "N/A")), "parcelas_total": int(row.get("total_parcelas", 0)),
                            "parcelas_pagas": int(row.get("parcelas_pagas", 0)), "data_nascimento": str(row.get("data_nascimento", "")),
                            "telefone": "".join(filter(str.isdigit, str(row.get("telefone", "")))), "data_processamento": datetime.now().isoformat()
                        }
                        sb.table(TA).upsert(payload).execute()
                    st.success("Sincronizado!")
            except Exception as e: st.error(f"Erro: {e}")
        res = sb.table(TA).select("*").eq("nome_empresa", st.session_state.n).execute()
        if res.data:
            df_res = pd.DataFrame(res.data)
            busca = st.text_input("🔍 Buscar")
            if busca: df_res = df_res[df_res["nome_funcionario"].str.contains(busca, case=False)]
            st.dataframe(df_res, use_container_width=True)

# --- ABA ADMIN ---
def aba_admin():
    st.markdown("### ⚙️ MASTER")
    pw = st.sidebar.text_input("Chave Master", type="password")
    if pw == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            st.write("Novo Cadastro")
            rz, cj = st.text_input("Razão"), st.text_input("CNPJ")
            lo, se = st.text_input("Login"), st.text_input("Senha", type="password")
            lk = st.text_input("Link CSV")
            if st.form_submit_button("SALVAR"):
                dt = {"nome_empresa":rz, "cnpj":cj, "login":lo, "senha":h(se), "link_planilha":lk}
                try:
                    sb.table(TE).insert(dt).execute(); st.success("Salvo!")
                except Exception as e: st.error(f"Erro: {e}")

# --- NAVEGAÇÃO ---
m = st.sidebar.radio("Menu", ["Funcionário", "Empresa", "Admin"])
if m == "Funcionário": aba_funcionario()
elif m == "Empresa": aba_empresa()
else: aba_admin()
