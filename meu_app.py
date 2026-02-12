import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.05);
        padding: 15px 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    @media (prefers-color-scheme: dark) { .logo-text { color: #4A90E2; } }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:gray; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

# --- 2. CONEXÃO E AUXILIARES ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("⚠️ Configurações de banco de dados não detectadas nos Secrets.")
        st.stop()
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if st.session_state.get('at'):
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Sair do Painel"):
        logout()

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para consultar sua auditoria.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA", use_container_width=True) and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                # Pega o registro mais recente (ou por ID de contrato se preferir)
                d = r.data[-1]
                # Validação simples de segurança
                if str(dt_nasc_in) == str(d.get("data_nascimento", "")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Olá, {d.get('nome_funcionario')}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Valor em Folha (RH)", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Instituição Bancária", d.get('banco_nome', 'N/A'))
                    
                    status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status da Auditoria", status)
                    
                    with st.expander("📊 Detalhes do Contrato e Evolução"):
                        st.write(f"**ID Contrato:** {d.get('contrato_id')}")
                        pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                        st.write(f"**Parcelas:** {pp} de {pt}")
                        if pt > 0: st.progress(min(pp/pt, 1.0))
                else: st.error("Dados de validação não conferem. Verifique a data e o telefone.")
            else: st.warning("CPF não localizado em nossa base.")
        except: st.error("Erro na comunicação com o servidor.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel de Gestão Empresarial")
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        with st.form("login_empresa"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type='password')
            if st.form_submit_button("ACESSAR PAINEL"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.at = True
                    st.session_state.n = q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Credenciais inválidas.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        
        # Carregamento de dados do Supabase
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        if not df_empresa.empty:
            # --- 4. DASHBOARD E MÉTRICAS ---
            c_m1, c_m2, c_m3 = st.columns(3)
            total = len(df_empresa)
            conf = len(df_empresa[df_empresa['diferenca'] == 0])
            divs = total - conf
            
            c_m1.metric("Total de Funcionários", total)
            c_m2.metric("Casos em Conformidade", conf)
            c_m3.metric("Divergências Detectadas", divs, delta=f"{divs} pendências", delta_color="inverse")
            
            # Gráfico de Resumo
            
            fig = px.pie(values=[conf, divs], names=['Conforme', 'Divergente'], 
                         color_discrete_sequence=['#2ecc71', '#e74c3c'], hole=0.4, height=300)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        # Ações de Sincronia e Exportação
        c_act1, c_act2, c_act3 = st.columns([1, 1, 2])
        with c_act1:
            if st.button("🔄 SINCRONIZAR PLANILHA", use_container_width=True):
                if not st.session_state.lk:
                    st.error("URL da planilha não configurada.")
                else:
                    try:
                        with st.spinner("Processando dados do CSV..."):
                            df_csv = pd.read_csv(st.session_state.lk)
                            df_csv.columns = df_csv.columns.str.strip().str.lower()
                            
                            payloads = []
                            for _, r in df_csv.iterrows():
                                vr = float(pd.to_numeric(r.get('valor_rh'), errors='coerce') or 0)
                                vb = float(pd.to_numeric(r.get('valor_banco'), errors='coerce') or 0)
                                payloads.append({
                                    "nome_empresa": st.session_state.n, 
                                    "cpf": "".join(filter(str.isdigit, str(r.get('cpf', "")))),
                                    "nome_funcionario": str(r.get('nome', 'N/A')), 
                                    "valor_rh": vr, "valor_banco": vb,
                                    "valor_emprestimo": float(pd.to_numeric(r.get('valor_emprestimo'), errors='coerce') or 0),
                                    "diferenca": round(vr - vb,
