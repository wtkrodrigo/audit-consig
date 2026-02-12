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
    }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .stProgress > div > div > div > div { background-color: #002D62; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"<div class='logo-text'>🛡️ RRB SOLUÇÕES | <span style='font-weight:normal; font-size:18px;'>{titulo}</span></div>", unsafe_allow_html=True)
    st.divider()

# --- 2. CONEXÃO E SEGURANÇA ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("⚠️ Configurações de banco de dados (Secrets) não encontradas.")
        st.stop()
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para consultar sua auditoria de consignados.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA", use_container_width=True) and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                # Validação Rigorosa
                if str(dt_nasc_in) == str(d.get("data_nascimento")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Bem-vindo, {d.get('nome_funcionario')}")
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Valor Banco", f"R$ {d.get('valor_banco', 0):,.2f}")
                    m3.metric("Diferença", f"R$ {d.get('diferenca', 0):,.2f}", 
                              delta=d.get('diferenca'), delta_color="inverse")
                    m4.metric("Banco", d.get('banco_nome', 'N/A'))
                    
                    with st.expander("📊 Detalhes do Empréstimo"):
                        st.write(f"**Contrato ID:** {d.get('contrato_id', 'N/A')}")
                        st.write(f"**Valor Total Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                        pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                        st.write(f"**Parcelas:** {pp} de {pt}")
                        if pt > 0:
                            st.progress(min(pp/pt, 1.0))
                else:
                    st.error("Dados de validação incorretos.")
            else:
                st.warning("CPF não localizado na base de dados.")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False

    if not st.session_state.at:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        res = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

        if not df.empty:
            c1, c2, c3 = st.columns(3)
            conf = len(df[df['diferenca'] == 0])
            err = len(df) - conf
            c1.metric("Total Base", len(df))
            c2.metric("Conformes", conf)
            c3.metric("Divergentes", err, delta=err, delta_color="inverse")
            
            fig = px.pie(values=[conf, err], names=['Conforme', 'Divergente'], 
                         color_discrete_sequence=['#2ecc71', '#e74c3c'], hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔄 SINCRONIZAR CSV", use_container_width=True):
                try:
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
                            "diferenca": round(vr - vb, 2),
                            "banco_nome": str(r.get('banco', 'N/A')),
                            "contrato_id": str(r.get('contrato', 'N/A')),
                            "parcelas_total": int(pd.to_numeric(r.get('total_parcelas'), errors='coerce') or 0),
                            "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas'), errors='coerce') or 0),
                            "data_nascimento": str(r.get('data_nascimento', '')),
                            "telefone": "".join(filter(str.isdigit, str(r.get('telefone', "")))),
                            "data_processamento": datetime.now().isoformat()
                        })
                    if payloads:
                        sb.table("resultados_auditoria").upsert(payloads).execute()
                        st.balloons()
                        st.rerun()
                except Exception as e: st.error(f"Erro: {e}")
        
        with col_btn2:
            if st.button("🚪 SAIR", use_container_width=True):
                st.session_state.at = False
                st.rerun()

        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)

# --- MÓDULO ADMIN ---
elif menu == "⚙️ Admin Master":
    render_header("Admin Master")
    if st.sidebar.text_input("Senha Master", type="password") == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("cad_full"):
            c1, c2, c3 = st.columns(3)
            razao = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            plano = c3.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
            
            c4, c5, c6 = st.columns(3)
            rep = c4.text_input("Representante")
            tel = c5.text_input("Telefone")
            end = c6.text_input("Endereço")
            
            c7, c8, c9 = st.columns(3)
            lo = c7.text_input("Login")
            se = c8.text_input("Senha", type="password")
            lk = c9.text_input("URL Planilha CSV")
            
            if st.form_submit_button("CADASTRAR EMPRESA"):
                sb.table("empresas").insert({
                    "nome_empresa": razao, "cnpj": cnpj, "plano": plano,
                    "representante": rep, "telefone": tel, "endereco": end,
                    "login": lo, "senha": h(se), "link_planilha": lk
                }).execute()
                st.success("Sucesso!")
