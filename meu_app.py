import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f4f7f9; }
    
    /* Forçar cores nas métricas */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6 !important;
        padding: 15px !important;
        border-radius: 12px !important;
    }

    [data-testid="stMetricLabel"] p {
        color: #444444 !important;
        font-weight: 600 !important;
    }

    [data-testid="stMetricValue"] div {
        color: #002D62 !important;
        font-weight: 800 !important;
    }

    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>""", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Erro nos Secrets. Verifique as chaves do Supabase.")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    
    with st.container():
        st.info("🔐 Informe seus dados para liberar a consulta.")
        c1, c2, c3 = st.columns([2, 2, 1])
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = c3.text_input("Final Tel (4 dígitos)", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA") and c_clean:
        try:
            # AQUI ESTAVA O ERRO DE IDENTAÇÃO
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            
            if r.data:
                d = r.data[-1]
                val_data = str(dt_nasc_in) == str(d.get("data_nascimento", ""))
                val_fone = str(d.get("telefone", "")).endswith(tel_fim_in)
                
                if val_data and val_fone:
                    st.success(f"Bem-vindo, {d['nome_funcionario']}")
                    
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    with m2:
                        st.metric("Banco", d.get('banco_nome', 'N/A'))
                    with m3:
                        stt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                        st.metric("Status", stt)
                        
                    with st.expander("📊 Detalhes do Contrato", expanded=True):
                        st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                        pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                        st.write(f"**Parcelas:** {pp} de {pt}")
                        if pt > 0: 
                            st.progress(min(pp/pt, 1.0))
                else:
                    st.error("Dados de validação incorretos (Data ou Telefone).")
            else:
                st.warning("CPF não localizado.")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: 
        st.session_state.at = False
        
    if not st.session_state.at:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else: 
                st.error("Login inválido.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        with c_act1:
            if st.button("🔄 SINCRONIZAR AGORA"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0)
                        vb = float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                        payload = {
                            "nome_empresa": st.session_state.n, 
                            "cpf": "".join(filter(str.isdigit, str(r['cpf']))),
                            "nome_funcionario": str(r['nome']), 
                            "valor_rh": vr, "valor_banco": vb,
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
                        sb.table("resultados_auditoria").upsert(payload).execute()
                    st.success("Sincronizado!"); st.rerun()
                except Exception as e: 
                    st.error(f"Erro: {e}")

        with c_act2:
            if not df_empresa.empty:
                st.download_button("📥 EXPORTAR CSV", df_empresa.to_csv(index=False).encode('utf-8'), "auditoria.csv", "text/csv")

        st.divider()
        busca = st.text_input("🔍 Pesquisar funcionário")
        if not df_empresa.empty:
            if busca:
                df_empresa = df_empresa[df_empresa['nome_funcionario'].str.contains(busca, case=False, na=False)]
            st.dataframe(df_empresa, use_container_width=True, hide_index=True)

# --- MÓDULO ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm_master"):
            st.subheader("📝 Cadastrar Nova Empresa")
            c1, c2, c3 = st.columns([2, 1, 1])
            razao, cnpj, plano = c1.text_input("Razão Social"), c2.text_input("CNPJ"), c3.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
            c7, c8, c9 = st.columns(3)
            lo, se, lk = c7.text_input("Login Admin"), c8.text_input("Senha", type='password'), c9.text_input("URL Planilha (CSV)")
            if st.form_submit_button("✅ SALVAR EMPRESA"):
                if razao and lo and se:
                    dt = {
                        "nome_empresa": razao, "cnpj": cnpj, "plano": plano, 
                        "login": lo, "senha": h(se), "link_planilha": lk,
                        "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    try:
                        sb.table("empresas").insert(dt).execute()
                        st.success("Empresa cadastrada!"); st.rerun()
                    except Exception as e: 
                        st.error(f"Erro: {e}")
