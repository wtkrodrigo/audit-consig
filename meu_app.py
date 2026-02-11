import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("Configurações do Supabase não encontradas.")
        st.stop()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    
    with st.container():
        st.info("Para sua segurança, valide seus dados abaixo para acessar a auditoria.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        # Campo de data com formato brasileiro
        dt_nasc = c2.date_input("Data de Nascimento", min_value=datetime(1940, 1, 1), format="DD/MM/YYYY")
        tel_fim = st.text_input("Últimos 4 dígitos do seu telefone celular", max_chars=4)
        
        c_clean = "".join(filter(str.isdigit, cpf_in))
        
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        try:
            # Busca filtrando por CPF
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            
            if r.data:
                d = r.data[-1]
                
                # Validação de Segurança (Data de Nascimento e Final do Telefone)
                # Nota: Assume-se que no DB a data está em YYYY-MM-DD e telefone é string
                db_dt_nasc = str(d.get('data_nascimento', ''))
                db_tel = str(d.get('telefone', ''))
                
                valid_dt = str(dt_nasc) == db_dt_nasc
                valid_tel = db_tel.endswith(tel_fim) if tel_fim else False

                if valid_dt and valid_tel:
                    st.success(f"Autenticação confirmada! Bem-vindo, {d['nome_funcionario']}")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Banco", d.get('banco_nome', 'N/A'))
                    status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status", status)
                    
                    with st.expander("Detalhamento do Contrato e Parcelas"):
                        col_a, col_b = st.columns(2)
                        col_a.write(f"**Valor do Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                        col_a.write(f"**Contrato:** {d.get('contrato_id', 'N/A')}")
                        
                        # Exibição de parcelas pagas / totais
                        p_pagas = d.get('parcelas_pagas', 0)
                        p_total = d.get('parcelas_total', 0)
                        col_b.write(f"**Parcelas Pagas:** {p_pagas}")
                        col_b.write(f"**Total de Parcelas:** {p_total}")
                        
                        # Barra de progresso visual do pagamento
                        if p_total > 0:
                            progresso = min(p_pagas / p_total, 1.0)
                            st.progress(progresso, text=f"Progresso do Contrato: {int(progresso*100)}%")
                else:
                    st.error("Dados de validação (Data de Nascimento ou Telefone) não conferem.")
            else:
                st.warning("Nenhum registro encontrado para este CPF.")
        except Exception as e:
            st.error(f"Erro ao validar dados: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u = st.text_input("Usuário Corporativo")
        p = st.text_input("Senha", type='password')
        if st.button("ACESSAR PAINEL"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.sidebar.button("FINALIZAR SESSÃO"):
            st.session_state.at = False; st.rerun()
            
        if st.button("🔄 SINCRONIZAR PLANILHA AGORA"):
            try:
                with st.spinner("Sincronizando..."):
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, row in df.iterrows():
                        vr = float(pd.to_numeric(row.get('valor_rh', 0), 'coerce') or 0)
                        vb = float(pd.to_numeric(row.get('valor_banco', 0), 'coerce') or 0)
                        payload = {
                            "nome_empresa": st.session_state.n,
                            "cpf": "".join(filter(str.isdigit, str(row['cpf']))),
                            "nome_funcionario": str(row['nome']),
                            "valor_rh": vr, "valor_banco": vb,
                            "valor_emprestimo": float(pd.to_numeric(row.get('valor_emprestimo', 0), 'coerce') or 0),
                            "diferenca": round(vr - vb, 2),
                            "banco_nome": str(row.get('banco', 'N/A')),
                            "contrato_id": str(row.get('contrato', 'N/A')),
                            "parcelas_total": int(pd.to_numeric(row.get('total_parcelas', 0), 'coerce') or 0),
                            "parcelas_pagas": int(pd.to_numeric(row.get('parcelas_pagas', 0), 'coerce') or 0),
                            "data_nascimento": str(row.get('data_nascimento', '')),
                            "telefone": "".join(filter(str.isdigit, str(row.get('telefone', '')))),
                            "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_auditoria").upsert(payload).execute()
                    st.success("Dados atualizados!")
            except Exception as e: st.error(f"Erro: {e}")

        st.divider()
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        if res_db.data:
            df_res = pd.DataFrame(res_db.data)
            busca = st.text_input("🔍 Buscar Funcionário")
            if busca:
                df_res = df_res[df_res['nome_funcionario'].str.contains(busca, case=False)]
            st.dataframe(df_res, use_container_width=True)

# --- MÓDULO ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    check_p = st.sidebar.text_input("Chave Master", type='password')
    if check_p == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("cadastro"):
            razao = st.text_input("Razão Social")
            log_e = st.text_input("Login Administrativo")
            sen_e = st.text_input("Senha", type='password')
            link_c = st.text_input("Link CSV")
            if st.form_submit_button("SALVAR"):
                d = {"nome_empresa": razao, "login": log
