import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #002D62 0%, #0056b3 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 25px;
    }
    [data-testid="stMetric"] {
        background: rgba(28, 131, 225, 0.05);
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #002D62;
    }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; align-items: center; gap: 20px;">
            <span style="font-size: 40px;">🛡️</span>
            <div>
                <h1 style="margin:0; font-size: 22px;">RRB SOLUÇÕES AUDITORIA</h1>
                <p style="margin:0; opacity: 0.8;">{titulo}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Erro nas credenciais do Supabase.")
        return None

sb = init_connection()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- 4. MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Colaborador")
    c1, c2, c3 = st.columns([2, 2, 1])
    cpf_in = c1.text_input("CPF (somente números)")
    dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
    tel_fim_in = c3.text_input("Finais do Telefone (4 dígitos)", max_chars=4)
    
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA", use_container_width=True, type="primary"):
        if c_clean and sb:
            try:
                r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
                if r.data:
                    d = r.data[-1]
                    # Validação de segurança
                    if str(dt_nasc_in) == str(d.get("data_nascimento")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                        st.success(f"Bem-vindo, {d.get('nome_funcionario')}")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                        m2.metric("Banco", d.get('banco_nome', 'N/A'))
                        diff = d.get('diferenca', 0)
                        stt = "✅ CONFORME" if diff == 0 else "⚠️ DIVERGÊNCIA"
                        m3.metric("Status", stt, delta=f"R$ {diff:,.2f}" if diff != 0 else None, delta_color="inverse")
                        
                        with st.expander("📊 Detalhes do Contrato", expanded=True):
                            st.write(f"**ID Contrato:** {d.get('contrato_id')}")
                            pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 1))
                            st.write(f"**Parcelas:** {pp} de {pt}")
                            st.progress(min(pp/pt, 1.0))
                    else:
                        st.error("Dados de nascimento ou telefone incorretos.")
                else:
                    st.warning("Dados não localizados para este CPF.")
            except:
                st.error("Erro ao consultar banco de dados.")

# --- 5. MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ACESSAR", use_container_width=True):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at = True
                st.session_state.n = q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else: st.error("Login ou senha inválidos.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        if not df_empresa.empty:
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Total Base", len(df_empresa))
            c_m2.metric("Conformes", len(df_empresa[df_empresa['diferenca'] == 0]))
            c_m3.metric("Divergentes", len(df_empresa[df_empresa['diferenca'] != 0]), delta_color="inverse")
        
        st.divider()
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        with c_act1:
            if st.button("🔄 SINCRONIZAR CSV", use_container_width=True):
                try:
                    with st.spinner("Processando..."):
                        df = pd.read_csv(st.session_state.lk)
                        df.columns = df.columns.str.strip().str.lower()
                        payloads = []
                        for _, r in df.iterrows():
                            vr = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0)
                            vb = float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                            payloads.append({
                                "nome_empresa": st.session_state.n, 
                                "cpf": "".join(filter(str.isdigit, str(r.get('cpf', "")))),
                                "nome_funcionario": str(r.get('nome', 'N/A')), 
                                "valor_rh": vr, "valor_banco": vb,
                                "diferenca": round(vr - vb, 2),
                                "banco_nome": str(r.get('banco', 'N/A')),
                                "contrato_id": str(r.get('contrato', 'N/A')),
                                "parcelas_total": int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0),
                                "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas', 0), 'coerce') or 0),
                                "data_nascimento": str(r.get('data_nascimento', '')),
                                "telefone": "".join(filter(str.isdigit, str(r.get('telefone', "")))),
                                "data_processamento": datetime.now().isoformat()
                            })
                        if payloads:
                            sb.table("resultados_auditoria").upsert(payloads, on_conflict="cpf, contrato_id").execute()
                            st.toast("Base atualizada!"); st.rerun()
                except Exception as e: st.error(f"Erro no CSV: {e}")

        with c_act2:
            if st.sidebar.button("🚪 Sair"): logout()

        busca = st.text_input("🔍 Pesquisar Nome ou CPF")
        if not df_empresa.empty:
            df_f = df_empresa.copy()
            if busca: 
                df_f = df_f[df_f['nome_funcionario'].str.contains(busca, case=False) | df_f['cpf'].str.contains(busca)]
            st.dataframe(df_f, use_container_width=True, hide_index=True)

# --- 6. ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            c1, c2 = st.columns(2)
            razao = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            lo = c1.text_input("Login Administrativo")
            se = c2.text_input("Senha", type='password')
            lk = st.text_input("URL Planilha (CSV)")
            if st.form_submit_button("✅ SALVAR EMPRESA"):
                if razao and lo and se:
                    dt = {"nome_empresa": razao, "cnpj": cnpj, "login": lo, "senha": h(se), "link_planilha": lk}
                    sb.table("empresas").insert(dt).execute()
                    st.success("Cadastrado!")
