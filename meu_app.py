import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    /* Fundo geral da página */
    .main { background-color: #f4f7f9; }
    
    /* Estilização dos Cards de Métrica */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Forçar cores dos textos das métricas para evitar que fiquem "brancos" */
    [data-testid="stMetricLabel"] {
        color: #555555 !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #002D62 !important;
        font-weight: 800 !important;
    }

    /* Cabeçalho e Logo */
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    
    /* Ajuste de botões */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
    }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>""", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nos Secrets. Verifique as chaves do Supabase."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    
    with st.container():
        st.info("🔐 Informe seus dados para liberar a consulta da sua auditoria.")
        c1, c2, c3 = st.columns([2, 2, 1])
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = c3.text_input("Final Telefone (4 dígitos)", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR MINHA AUDITORIA") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                # Validação Tripla
                val_data = str(dt_nasc_in) == str(d.get("data_nascimento", ""))
                val_fone = str(d.get("telefone", "")).endswith(tel_fim_in)
                
                if val_data and val_fone:
                    st.success(f"Bem-vindo(a), {d['nome_funcionario']}")
                    
                    # Seção de Métricas (Onde estava o erro visual)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Instituição Bancária", d.get('banco_nome', 'N/A'))
                    
                    status_val = d.get('diferenca', 0)
                    stt = "✅ CONFORME" if status_val == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status da Auditoria", stt)
                    
                    st.write("") # Espaçador
                    
                    with st.expander("📊 Detalhes do Contrato e Parcelas", expanded=True):
                        col_det1, col_det2 = st.columns(2)
                        with col_det1:
                            st.write(f"**Valor do Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                            st.write(f"**ID do Contrato:** {d.get('contrato_id', 'N/A')}")
                        
                        with col_det2:
                            pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                            st.write(f"**Progresso de Parcelas:** {pp} de {pt}")
                            if pt > 0: 
                                st.progress(min(pp/pt, 1.0))
                else:
                    st.error("Dados de validação não conferem. Verifique a Data de Nascimento e o Final do Telefone.")
            else:
                st.warning("CPF não localizado em nossa base de dados.")
        except Exception as e:
            st.error(f"Erro ao consultar banco de dados: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel de Gestão da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u = st.text_input("Usuário de Acesso")
        p = st.text_input("Senha", type='password')
        if st.button("ENTRAR NO PAINEL"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else: st.error("Credenciais inválidas.")
    else:
        st.subheader(f"Empresa: {st.session_state.n}")
        
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        with c_act1:
            if st.button("🔄 ATUALIZAR DADOS (CSV)"):
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
                    st.success("Dados sincronizados com sucesso!"); st.rerun()
                except Exception as e: st.error(f"Erro na sincronização: {e}")

        with c_act2:
            if not df_empresa.empty:
                st.download_button("📥 BAIXAR RELATÓRIO", df_empresa.to_csv(index=False).encode('utf-8'), "auditoria_rrb.csv", "text/csv")

        st.divider()
        busca = st.text_input("🔍 Localizar Funcionário (Nome ou CPF)")
        if not df_empresa.empty:
            if busca:
                df_empresa = df_empresa[df_empresa['nome_funcionario'].str.contains(busca, case=False, na=False) | df_empresa['cpf'].str.contains(busca, na=False)]
            st.dataframe(df_empresa, use_container_width=True, hide_index=True)

# --- MÓDULO ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Gestão Administrativa RRB")
    senha_master = st.sidebar.text_input("Chave de Segurança Master", type='password')
    
    if senha_master == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm_master"):
            st.subheader("📝 Cadastrar Nova Empresa Cliente")
            c1, c2, c3 = st.columns([2, 1, 1])
            razao = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            plano = c3.selectbox("Plano Contratado", ["Standard", "Premium", "Enterprise"])
            
            c4, c5, c6 = st.columns([1, 1, 2])
            rep = c4.text_input("Representante")
            tel = c5.text_input("Telefone Contato")
            end = c6.text_input("Endereço Sede")
            
            st.divider()
            c7, c8, c9 = st.columns(3)
            lo = c7.text_input("Login de Acesso")
            se = c8.text_input("Senha de Acesso", type='password')
            lk = c9.text_input("URL do CSV (Google Sheets)")
            
            if st.form_submit_button("✅ FINALIZAR CADASTRO"):
                if razao and lo and se:
                    dt = {
                        "nome_empresa": razao, "cnpj": cnpj, "representante": rep, 
                        "telefone": tel, "endereco": end, "plano": plano, 
                        "login": lo, "senha": h(se), "link_planilha": lk,
                        "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    try:
                        sb.table("empresas").insert(dt).execute()
                        st.success(f"Empresa {razao} cadastrada com sucesso!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro ao inserir: {e}")
        
        st.write("---")
        st.subheader("Empresas Ativas")
        try:
            em = sb.table("empresas").select("nome_empresa, cnpj, plano, data_expiracao").execute()
            if em.data: st.dataframe(pd.DataFrame(em.data), use_container_width=True, hide_index=True)
        except: pass
