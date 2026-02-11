import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        padding: 15px 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    @media (prefers-color-scheme: dark) { .logo-text { color: #4A90E2; } }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; text-align: center; color: gray; font-size: 12px; padding: 10px; background: transparent; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:var(--text-color); opacity: 0.6; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO E FUNÇÕES AUXILIARES ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro na conexão com o banco de dados. Verifique os Secrets."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. BARRA LATERAL E NAVEGAÇÃO ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/584/584796.png", width=80) # Ícone genérico de auditoria
    st.title("Menu Principal")
    menu = st.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
    
    st.write("---")
    if menu == "🏢 Empresa" and st.session_state.get('at'):
        if st.button("🚪 Sair da Sessão"):
            logout()
    
    # Direitos Autorais na Barra Lateral
    st.caption("© 2026 RRB Soluções Auditoria")
    st.caption("Todos os direitos reservados.")

# --- 4. MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para liberar a consulta de conformidade.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            if str(dt_nasc_in) == str(d.get("data_nascimento", "")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                st.success(f"Bem-vindo, {d['nome_funcionario']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                m2.metric("Banco", d.get('banco_nome', 'N/A'))
                
                status_val = d.get('diferenca', 0)
                stt = "✅ CONFORME" if status_val == 0 else "⚠️ DIVERGÊNCIA"
                m3.metric("Status", stt, delta=f"R$ {status_val:,.2f}" if status_val != 0 else None, delta_color="inverse")
                
                with st.expander("📊 Detalhes do Contrato"):
                    st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f} | **ID:** {d.get('contrato_id', 'N/A')}")
                    pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                    st.write(f"**Parcelas:** {pp} de {pt}")
                    if pt > 0: st.progress(min(pp/pt, 1.0))
            else: st.error("Dados de validação incorretos.")
        else: st.warning("CPF não localizado em nossa base de auditoria.")

# --- 5. MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    
    if 'at' not in st.session_state: st.session_state.at = False
    if 'reset_mode' not in st.session_state: st.session_state.reset_mode = False
    
    if not st.session_state.at:
        if not st.session_state.reset_mode:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type='password')
            if st.button("ACESSAR"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Login ou senha inválidos.")
            if st.button("Esqueci minha senha"):
                st.session_state.reset_mode = True; st.rerun()
        else:
            st.subheader("🔑 Recuperar Senha")
            user_reset = st.text_input("Usuário")
            cnpj_reset = st.text_input("CNPJ (apenas números)")
            nova_senha = st.text_input("Nova Senha", type="password")
            if st.button("ATUALIZAR SENHA"):
                check = sb.table("empresas").select("*").eq("login", user_reset).eq("cnpj", cnpj_reset).execute()
                if check.data:
                    sb.table("empresas").update({"senha": h(nova_senha)}).eq("login", user_reset).execute()
                    st.success("Senha atualizada!"); st.session_state.reset_mode = False; st.rerun()
                else: st.error("Dados não conferem.")
            if st.button("Voltar ao Login"):
                st.session_state.reset_mode = False; st.rerun()
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        if not df_empresa.empty:
            conf = len(df_empresa[df_empresa['diferenca'] == 0])
            div = len(df_empresa[df_empresa['diferenca'] != 0])
            c_c, c_s = st.columns([1, 2])
            with c_c:
                fig = go.Figure(data=[go.Pie(labels=['Conforme', 'Divergente'], values=[conf, div], hole=.6, marker_colors=['#28a745', '#dc3545'])])
                fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            with c_s:
                st.metric("Total de Funcionários", len(df_empresa))
                st.metric("Casos com Divergência", div, delta=f"{(div/len(df_empresa)*100):.1f}%" if len(df_empresa)>0 else None, delta_color="inverse")
        
        st.divider()
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        with c_act1:
            if st.button("🔄 SINCRONIZAR PLANILHA"):
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
                    st.success("Sincronizado!"); st.rerun()
                except Exception as e: st.error(f"Erro na sincronização: {e}")
        with c_act2:
            if not df_empresa.empty:
                st.download_button("📥 EXPORTAR CSV", df_empresa.to_csv(index=False).encode('utf-8'), "auditoria_rrb.csv", "text/csv")

        busca = st.text_input("🔍 Pesquisar funcionário (Nome ou CPF)")
        if not df_empresa.empty:
            if busca:
                df_empresa = df_empresa[df_empresa['nome_funcionario'].str.contains(busca, case=False, na=False) | df_empresa['cpf'].str.contains(busca, na=False)]
            st.dataframe(df_empresa, use_container_width=True, hide_index=True)

# --- 6. MÓDULO ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Painel de Controle Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm_master"):
            st.subheader("📝 Cadastrar Empresa")
            c1, c2, c3 = st.columns([2, 1, 1])
            razao, cnpj, plano = c1.text_input("Razão Social"), c2.text_input("CNPJ"), c3.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
            c7, c8, c9 = st.columns(3)
            lo, se, lk = c7.text_input("Login"), c8.text_input("Senha", type='password'), c9.text_input("URL Planilha CSV")
            if st.form_submit_button("✅ SALVAR"):
                if razao and lo and se:
                    dt = {"nome_empresa": razao, "cnpj": cnpj, "plano": plano, "login": lo, "senha": h(se), "link_planilha": lk}
                    sb.table("empresas").insert(dt).execute()
                    st.success("Cadastrada!"); st.rerun()
        st.divider()
        try:
            em = sb.table("empresas").select("nome_empresa, cnpj, plano").execute()
            if em.data: st.dataframe(pd.DataFrame(em.data), use_container_width=True)
        except: pass

# --- 7. TERMOS E PRIVACIDADE (RODAPÉ) ---
st.write("---")
with st.expander("⚖️ Termos de Uso e Política de Privacidade"):
    st.markdown(f"""
    **RRB SOLUÇÕES - PORTAL DE AUDITORIA** Este sistema é uma ferramenta de conformidade e auditoria financeira privada.
    
    1. **Propriedade Intelectual:** Todo o código e lógica de processamento são de propriedade da **RRB Soluções**. A reprodução não autorizada é proibida.
    2. **Finalidade:** O tratamento de dados (CPF e Nascimento) ocorre exclusivamente para validação de identidade e acesso aos registros de empréstimos informados pelo empregador.
    3. **Privacidade (LGPD):** Não compartilhamos dados com terceiros. As informações são armazenadas em ambiente seguro (Supabase) sob criptografia.
    4. **Limitação de Responsabilidade:** Os dados exibidos refletem as planilhas enviadas pelas empresas e bancos parceiros. A RRB Soluções atua como ferramenta de visualização e auditoria, não realizando descontos financeiros diretamente.
    
    *Última atualização: {datetime.now().strftime('%d/%m/%Y')}*
    """)

st.markdown("<div class='footer'>RRB SOLUÇÕES AUDITORIA - Sistema de Conformidade Financeira</div>", unsafe_allow_html=True)
