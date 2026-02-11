import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. DESIGN SYSTEM ADAPTATIVO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Métrica Adaptativa */
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px;
        border-radius: 16px;
        border-top: 5px solid #002D62;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* Cabeçalho Fixo */
    .header-box {
        background: linear-gradient(135deg, #002D62 0%, #001529 100%);
        padding: 25px; border-radius: 15px; color: white;
        margin-bottom: 30px; display: flex; align-items: center; gap: 20px;
    }

    /* Rodapé */
    .footer-note {
        font-size: 12px; color: var(--text-color); opacity: 0.6;
        text-align: center; margin-top: 50px; padding: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
    }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class="header-box">
        <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 12px;">
            <span style="font-size: 35px;">🛡️</span>
        </div>
        <div>
            <div style="font-size: 26px; font-weight: 800; line-height: 1.1; color: white;">RRB SOLUÇÕES</div>
            <div style="font-size: 15px; opacity: 0.8; color: white;">{titulo}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    st.markdown(f"""
    <div class="footer-note">
        <p>© {datetime.now().year} RRB Soluções em Auditoria. Todos os direitos reservados.</p>
        <p><b>Privacidade e Segurança:</b> Este sistema utiliza criptografia de ponta a ponta. 
        Dados protegidos pela LGPD.</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA ---
@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

sb = get_supabase()
if not sb:
    st.error("Erro na conexão. Verifique os Secrets.")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- 3. BARRA LATERAL COM CENTRAL DE SUPORTE ---
with st.sidebar:
    st.markdown("### 🧭 Portal de Acesso")
    menu = st.radio("Selecione o Nível:", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"], label_visibility="collapsed")
    
    st.write("---")
    st.markdown("### 🛠️ Central de Ajuda")
    with st.expander("❓ Problemas Comuns"):
        st.info("**Erro no CSV?** Verifique se as colunas 'CPF' e 'Valor_RH' existem.")
        st.info("**Login Inválido?** Confirme se o Caps Lock está ativado.")
        st.info("**Dados Desatualizados?** Clique em 'Sincronizar CSV'.")
    
    # Botão de Suporte via WhatsApp
    tel_suporte = "5511999999999" # COLOQUE SEU NÚMERO AQUI
    msg = "Olá Suporte RRB! Preciso de ajuda com o sistema de auditoria."
    link_wa = f"https://wa.me/{tel_suporte}?text={msg.replace(' ', '%20')}"
    
    st.markdown(f"""
        <a href="{link_wa}" target="_blank" style="text-decoration: none;">
            <div style="background-color: #25D366; color: white; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold;">
                💬 Chamar Suporte Técnico
            </div>
        </a>
    """, unsafe_allow_html=True)

    if (menu == "🏢 Empresa" and st.session_state.get('at')) or menu == "⚙️ Admin Master":
        st.write("---")
        if st.button("🚪 Sair da Sessão", use_container_width=True): logout()

# --- 4. MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Área do Colaborador")
    c1, c2 = st.columns(2)
    cpf_in = c1.text_input("🆔 CPF (apenas números)")
    dt_nasc_in = c2.date_input("📅 Data de Nascimento", min_value=datetime(1930,1,1))
    tel_fim_in = st.text_input("📞 Últimos 4 dígitos do telefone", max_chars=4)
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 CONSULTAR AUDITORIA", type="primary") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                if str(dt_nasc_in) == str(d.get("data_nascimento")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Olá, {d.get('nome_funcionario')}!")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("💰 Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("🏦 Instituição", d.get('banco_nome', 'N/A'))
                    stt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("📊 Status Final", stt)
                else: st.error("Dados incorretos.")
            else: st.warning("CPF não encontrado.")
        except: st.error("Erro na consulta.")
    render_footer()

# --- 5. MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Gestão Empresarial")
    if 'at' not in st.session_state: st.session_state.at = False
    if 'reset_mode' not in st.session_state: st.session_state.reset_mode = False
    
    if not st.session_state.at:
        if not st.session_state.reset_mode:
            u = st.text_input("👤 Usuário")
            p = st.text_input("🔒 Senha", type='password')
            if st.button("ENTRAR NO PAINEL", type="primary"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Acesso negado.")
            st.button("❓ Esqueci minha senha", on_click=lambda: st.session_state.update({"reset_mode": True}))
        else:
            st.markdown("#### 🔑 Recuperação")
            ur, cr, ns = st.text_input("👤 Usuário"), st.text_input("📄 CNPJ"), st.text_input("🆕 Nova Senha", type="password")
            if st.button("✅ ATUALIZAR"):
                check = sb.table("empresas").select("*").eq("login", ur).eq("cnpj", cr).execute()
                if check.data:
                    sb.table("empresas").update({"senha": h(ns)}).eq("login", ur).execute()
                    st.success("Senha atualizada!"); st.session_state.reset_mode = False; st.rerun()
                else: st.error("Dados inválidos.")
            st.button("⬅️ Voltar", on_click=lambda: st.session_state.update({"reset_mode": False}))
    else:
        st.subheader(f"🏢 Parceira: {st.session_state.n}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        if not df_empresa.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("👥 Colaboradores", len(df_empresa))
            c2.metric("✔️ Conformes", len(df_empresa[df_empresa['diferenca'] == 0]))
            c3.metric("🚨 Divergentes", len(df_empresa[df_empresa['diferenca'] != 0]))
        
        if st.button("🔄 SINCRONIZAR CSV"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                payloads = [{
                    "nome_empresa": st.session_state.n, 
                    "cpf": "".join(filter(str.isdigit, str(r.get('cpf', "")))),
                    "nome_funcionario": str(r.get('nome', 'N/A')), 
                    "valor_rh": float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0),
                    "valor_banco": float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0),
                    "diferenca": round(float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0) - float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0), 2),
                    "banco_nome": str(r.get('banco', 'N/A')),
                    "contrato_id": str(r.get('contrato', 'N/A')),
                    "parcelas_total": int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0),
                    "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas', 0), 'coerce') or 0),
                    "data_nascimento": str(r.get('data_nascimento', '')),
                    "telefone": "".join(filter(str.isdigit, str(r.get('telefone', "")))),
                    "data_processamento": datetime.now().isoformat()
                } for _, r in df.iterrows()]
                sb.table("resultados_auditoria").upsert(payloads, on_conflict="cpf, contrato_id").execute()
                st.toast("Sucesso!"); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

        busca = st.text_input("🔍 Buscar Nome ou CPF")
        if not df_empresa.empty:
            df_f = df_empresa.copy()
            if busca: df_f = df_f[df_f['nome_funcionario'].str.contains(busca, case=False, na=False)]
            st.dataframe(df_f, use_container_width=True, hide_index=True)
    render_footer()

# --- 6. ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações do Sistema")
    if st.sidebar.text_input("🔐 Chave Mestra", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            c1, c2, c3 = st.columns([2, 1, 1])
            razao, cnpj, plano = c1.text_input("🏢 Razão Social"), c2.text_input("📄 CNPJ"), c3.selectbox("💎 Plano", ["Standard", "Premium", "Enterprise"])
            c4, c5, c6 = st.columns([1, 1, 2])
            rep, tel, end = c4.text_input("👤 Representante"), c5.text_input("📞 Telefone"), c6.text_input("📍 Endereço")
            c7, c8, c9 = st.columns(3)
            lo, se, lk = c7.text_input("👤 Login"), c8.text_input("🔒 Senha", type='password'), c9.text_input("🔗 Link CSV")
            if st.form_submit_button("🚀 SALVAR NOVA PARCEIRA"):
                dt = {"nome_empresa": razao, "cnpj": cnpj, "representante": rep, "telefone": tel, "endereco": end, "plano": plano, "login": lo, "senha": h(se), "link_planilha": lk}
                sb.table("empresas").insert(dt).execute()
                st.success("Cadastrado!"); st.rerun()
    render_footer()
