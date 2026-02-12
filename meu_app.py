import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date

# ============================================================
# 0) CONFIGURAÇÃO E TEMA ADAPTATIVO
# ============================================================
st.set_page_config(page_title="RRB Auditoria", layout="wide")

# CSS Avançado: Slim, Dark/Light Mode Ready e WhatsApp Minimalista
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* Reset e Fonte */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Cores Variáveis (Adaptam ao Tema do Streamlit) */
    :root {
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(128, 128, 128, 0.2);
        --accent-color: #4A90E2;
    }

    /* Background Slim */
    .stApp {
        background: radial-gradient(circle at 20% 20%, rgba(74, 144, 226, 0.05) 0%, transparent 40%);
    }

    /* Cards Estilo Glassmorphism */
    .rrb-card {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        padding: 20px;
        backdrop-filter: blur(8px);
        margin-bottom: 15px;
    }

    /* Cabeçalho Slim */
    .slim-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        border-bottom: 1px solid var(--glass-border);
        padding-bottom: 10px;
    }

    /* Botão WhatsApp Flutuante Minimalista */
    .wpp-fab {
        position: fixed;
        bottom: 25px;
        right: 25px;
        background: #25D366;
        color: white !important;
        width: 50px;
        height: 50px;
        border-radius: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 1000;
        text-decoration: none;
        transition: transform 0.3s ease;
    }
    .wpp-fab:hover { transform: scale(1.1); }

    /* Rodapé de Privacidade */
    .footer-note {
        margin-top: 50px;
        padding: 20px;
        text-align: center;
        font-size: 11px;
        opacity: 0.6;
        border-top: 1px solid var(--glass-border);
    }

    /* Inputs e Botões Slim */
    .stButton > button {
        border-radius: 8px;
        border: none;
        background: var(--accent-color);
        color: white;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1) LÓGICA DE FUNDO (SEM ALTERAÇÃO DE DADOS)
# ============================================================
def sha256_hex(p: str): return hashlib.sha256(str(p).encode("utf-8")).hexdigest()
def digits_only(s: str): return "".join(filter(str.isdigit, str(s or "")))
def safe_float(v):
    try: return float(str(v).replace(',', '.')) if v else 0.0
    except: return 0.0

# Conexão Segura
@st.cache_resource
def get_sb():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    sb = get_sb()
except:
    st.error("Erro de conexão. Verifique os Secrets.")
    st.stop()

# ============================================================
# 2) COMPONENTES VISUAIS REUTILIZÁVEIS
# ============================================================
def render_footer():
    st.markdown(f"""
    <div class="footer-note">
        © {datetime.now().year} RRB Soluções em Auditoria. <br>
        Este sistema processa dados sob rigoroso protocolo de criptografia e conformidade com a LGPD. 
        Acesso restrito e monitorado.
    </div>
    """, unsafe_allow_html=True)

def render_wpp():
    st.markdown('<a href="https://wa.me/5513996261907" class="wpp-fab" target="_blank">💬</a>', unsafe_allow_html=True)

def render_slim_header(titulo):
    st.markdown(f"""
    <div class="slim-header">
        <span style="font-weight:800; font-size:20px; letter-spacing:-0.5px; color:var(--accent-color);">RRB / <span style="font-weight:300; color:inherit;">{titulo}</span></span>
        <span style="font-size:10px; opacity:0.5;">SISTEMA DE CONFORMIDADE V3.0</span>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 3) ABAS DO PROGRAMA
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- PORTAL FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_slim_header("AUDITORIA")
    st.markdown('<div class="rrb-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    cpf_in = c1.text_input("CPF")
    nasc_in = c2.date_input("Nascimento", min_value=date(1940, 1, 1), format="DD/MM/YYYY")
    tel_in = st.text_input("Últimos 4 dígitos do telefone", max_chars=4)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Validar e Acessar", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).order("data_processamento", desc=True).limit(1).execute()
        if res.data:
            d = res.data[0]
            if str(d.get("data_nascimento")) == nasc_in.strftime("%Y-%m-%d") and digits_only(d.get("telefone")).endswith(tel_in):
                st.success(f"Auditado: {d.get('nome_funcionario')}")
                m1, m2, m3 = st.columns(3)
                v_rh, v_bn = safe_float(d.get('valor_rh')), safe_float(d.get('valor_banco'))
                diff = safe_float(d.get('diferenca'))
                m1.metric("Valor RH", f"R$ {v_rh:,.2f}")
                m2.metric("Valor Banco", f"R$ {v_bn:,.2f}")
                m3.metric("Status", "✅" if abs(diff) < 0.05 else "⚠️", delta=f"{diff:,.2f}")
            else: st.error("Dados de validação incorretos.")
        else: st.info("Registro não localizado.")
    
    render_wpp()
    render_footer()

# --- PORTAL EMPRESA ---
elif menu == "🏢 Empresa":
    render_slim_header("PAINEL EMPRESA")
    if "auth_ok" not in st.session_state: st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        with st.form("login_slim"):
            u = st.text_input("ID")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    st.session_state.update({"auth_ok": True, "e_nome": q.data[0].get("nome_empresa"), "e_url": q.data[0].get("link_planilha")})
                    st.rerun()
                else: st.error("Falha no login.")
    else:
        st.caption(f"Logado como: {st.session_state.e_nome}")
        if st.button("🔄 Sincronizar Base de Dados"):
            try:
                df = pd.read_csv(st.session_state.e_url)
                df.columns = df.columns.str.strip().str.lower()
                payload = []
                for _, r in df.iterrows():
                    vr, vb = safe_float(r.get('valor_rh')), safe_float(r.get('valor_banco'))
                    payload.append({
                        "nome_empresa": st.session_state.e_nome,
                        "cpf": digits_only(str(r.get('cpf'))),
                        "nome_funcionario": str(r.get('nome')),
                        "valor_rh": vr, "valor_banco": vb, "diferenca": round(vr - vb, 2),
                        "banco_nome": str(r.get('banco')), "contrato_id": str(r.get('contrato')),
                        "data_nascimento": str(r.get('data_nascimento')),
                        "telefone": digits_only(str(r.get('telefone'))),
                        "data_processamento": datetime.now().isoformat()
                    })
                sb.table("resultados_auditoria").upsert(payload, on_conflict="nome_empresa,cpf,contrato_id").execute()
                st.toast("Dados Atualizados!")
            except Exception as e: st.error(f"Erro: {e}")
        
        if st.sidebar.button("Encerrar Sessão"):
            del st.session_state.auth_ok
            st.rerun()

    render_wpp()
    render_footer()

# --- ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_slim_header("MASTER CONTROL")
    if st.sidebar.text_input("Chave", type="password") == st.secrets.get("SENHA_MASTER"):
        with st.form("add_e"):
            st.markdown("### Nova Empresa")
            n = st.text_input("Nome da Empresa")
            l = st.text_input("Login")
            s = st.text_input("Senha", type="password")
            u = st.text_input("URL da Planilha")
            if st.form_submit_button("Cadastrar Parceiro"):
                sb.table("empresas").insert({"nome_empresa": n, "login": l, "senha": sha256_hex(s), "link_planilha": u}).execute()
                st.success("Cadastrado com sucesso.")
    
    render_footer()
