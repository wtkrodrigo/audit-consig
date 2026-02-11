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
    # HTML dividido para evitar que o GitHub corte a linha
    h_start = "<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>"
    h_content = f"<div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>"
    h_end = "</div>"
    st.markdown(h_start + h_content + h_end, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    # Verificação robusta de secrets
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("Erro: Configurações do Supabase não encontradas nos Secrets.")
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
        st.info("Valide seus dados abaixo para acessar sua auditoria.")
        col_f1, col_f2 = st.columns(2)
        cpf_input = col_f1.text_input("Digite seu CPF (apenas números)")
        data_nasc = col_f2.date_input("Data de Nascimento", min_value=datetime(1940, 1, 1), format="DD/MM/YYYY")
        telefone_fim = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        
        c_clean = "".join(filter(str.isdigit, cpf_input))
        
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        try:
            res_func = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if res_func.data:
                d = res_func.data[-1]
                # Validação Dupla: Data de Nascimento e Final do Telefone
                valid_dt = (str(data_nasc) == str(d.get("data_nascimento", "")))
                valid_tl = str(d.get("telefone", "")).endswith(telefone_fim)
                
                if valid_dt and valid_tl:
                    st.success(f"Bem-vindo, {d['nome_funcionario']}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Banco", d.get('banco_nome', 'N/A'))
                    status_txt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status", status_txt)
                    
                    with st.expander("📊 Detalhamento do Contrato"):
                        p_pago = int(d.get("parcelas_pagas", 0))
                        p_total = int(d.get("parcelas_total", 0))
                        st.write(f"**Contrato:** {d.get('contrato_id', 'N/A')}")
                        st.write(f"**Valor Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                        st.write(f"**Parcelas:** {p_pago} pagas de {p_total} totais")
                        if p_total > 0:
                            progresso = min(p_pago / p_total, 1.0)
                            st.progress(progresso, text=f"Progresso: {int(progresso*100)}%")
                else:
                    st.error("Dados de validação incorretos. Verifique a Data ou o Telefone.")
            else:
                st.warning("Nenhum registro encontrado para este CPF.")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if "at" not in st.session_state:
        st.session_state.at = False
    
    if not st.session_state.at:
        u_login = st.text_input("Usuário Corporativo")
        u_senha = st.text_input("Senha", type="password")
        if st.button("ACESSAR PAINEL"):
            try:
                q_emp = sb.table("empresas").select("*").eq("login", u_login).execute()
                if q_emp.data and h(u_senha) == q_emp.data[0]["senha"]:
                    st.session_state.at = True
                    st.session_state.n = q_emp.data[0]["nome_empresa"]
                    st.session_state.lk = q_emp.data[0].get("link_planilha")
                    st.rerun()
                else:
                    st.error("Acesso negado. Login ou senha inválidos.")
            except Exception as e:
                st.error(f"Erro na autenticação: {e}")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.sidebar.button("FINALIZAR SESSÃO"):
            st.session_state.at = False
            st.rerun()

        if st.button("🔄 SINCRONIZAR PLANILHA AGORA"):
            try:
                with st.spinner("Processando dados..."):
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, row in df.iterrows():
                        v_rh = float(pd.to_numeric(row.get("valor_rh", 0), "coerce") or 0)
                        v_bn = float(pd.to_numeric(row.get("valor_banco", 0), "coerce") or 0)
                        p_load = {
                            "nome_empresa": st.session_state.n,
                            "cpf": "".join(filter(str.isdigit, str(row["cpf"]))),
                            "nome_funcionario": str(row["nome"]),
                            "valor_rh": v_rh,
                            "valor_banco": v_bn,
                            "valor_emprestimo": float(pd.to_numeric(row.get("valor_emprestimo", 0), "coerce") or 0),
                            "diferenca": round(v_rh - v_bn, 2),
                            "banco_nome": str(row.get("banco", "N/A")),
                            "contrato_id": str(row.get("contrato", "N/A")),
                            "parcelas_total": int(pd.to_numeric(row.get("total_parcelas", 0), "coerce") or 0),
                            "parcelas_pagas": int(pd.to_numeric(row.get("parcelas_pagas", 0), "coerce") or 0),
                            "data_nascimento": str(row.get("data_nascimento", "")),
                            "telefone": "".join(filter(str.isdigit, str(row.get("telefone", "")))),
                            "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_
