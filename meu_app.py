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
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px;
        border-radius: 16px;
        border-top: 5px solid #002D62;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .header-box {
        background: linear-gradient(135deg, #002D62 0%, #001529 100%);
        padding: 25px; border-radius: 15px; color: white;
        margin-bottom: 30px; display: flex; align-items: center; gap: 20px;
    }
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
    ano = datetime.now().year
    st.markdown(f"""
    <div class="footer-note">
        <p>© {ano} RRB Soluções em Auditoria. Todos os direitos reservados.</p>
        <p><b>Privacidade e Segurança:</b> Este sistema utiliza criptografia de ponta a ponta. 
        Proteção total conforme LGPD.</p>
    </div>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

sb = get_supabase()
if not sb:
    st.error("Erro na conexão com o banco. Verifique os Secrets.")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. SIDEBAR COM SUPORTE ATUALIZADO ---
with st.sidebar:
    st.markdown("### 🧭 Menu Principal")
    menu = st.radio("Selecione o Nível:", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"], label_visibility="collapsed")
    
    st.write("---")
    st.markdown("### 🛠️ Central de Ajuda")
    with st.expander("❓ Problemas Comuns"):
        st.info("**Login?** Verifique maiúsculas/minúsculas.")
        st.info("**CPF?** Use apenas números.")
    
    tel_suporte = "5513996261007" 
    msg_wa = "Olá! Preciso de suporte no sistema RRB Soluções."
    link_wa = f"https://wa.me/{tel_suporte}?text={msg_wa.replace(' ', '%20')}"
    
    st.markdown(f"""
        <a href="{link_wa}" target="_blank" style="text-decoration: none;">
            <div style="background-color: #25D366; color: white; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold;">
                💬 Suporte via WhatsApp
            </div>
        </a>
    """, unsafe_allow_html=True)

    if (menu == "🏢 Empresa" and st.session_state.get('at')) or menu == "⚙️ Admin Master":
        st.write("---")
        if st.button("🚪 Sair da Sessão", use_container_width=True):
            logout()

# --- 4. MÓDULOS ---
if menu == "👤 Funcionário":
    render_header("Portal do Colaborador")
    c1, c2 = st.columns(2)
    cpf_in = c1.text_input("🆔 CPF")
    dt_nasc_in = c2.date_input("📅 Data de Nascimento", min_value=datetime(1930,1,1))
    tel_fim_in = st.text_input("📞 Últimos 4 dígitos do telefone", max_chars=4)
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 CONSULTAR", type="primary") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                if str(dt_nasc_in) == str(d.get("data_nascimento")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Bem-vindo, {d.get('nome_funcionario')}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("💰 Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("🏦 Instituição", d.get('banco_nome', 'N/A'))
                    m3.metric("📊 Status", "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGENTE")
                else:
                    st.error("Dados não conferem.")
            else:
                st.warning("Não localizado.")
        except:
            st.error("Erro na base.")
    render_footer()

elif menu == "🏢 Empresa":
    render_header("Painel Corporativo")
    if 'at' not in st.session_state: st.session_state.at = False
    if 'reset_mode' not in st.session_state: st.session_state.reset_mode = False
    
    if not st.session_state.at:
        if not st.session_state.reset_mode:
            u = st.text_input("👤 Usuário")
            p = st.text_input("🔒 Senha", type='password')
            if st.button("ENTRAR", type="primary"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.update({'at': True, 'n': q.data[0]['nome_empresa'], 'lk': q.data[0].get('link_planilha')})
                    st.rerun()
                else:
                    st.error("Login ou senha inválidos.")
            st.button("❓ Esqueci minha senha", on_click=lambda: st.session_state.update({"reset_mode": True}))
        else:
            ur, cr, ns = st.text_input("👤 Usuário"), st.text_input("📄 CNPJ"), st.text_input("🆕 Nova Senha", type="password")
            if st.button("✅ ATUALIZAR"):
                check = sb.table("empresas").select("*").eq("login", ur).eq("cnpj", cr).execute()
                if check.data:
                    sb.table("empresas").update({"senha": h(ns)}).eq("login", ur).execute()
                    st.success("Senha atualizada!"); st.session_state.reset_mode = False; st.rerun()
            st.button("⬅️ Voltar", on_click=lambda: st.session_state.update({"reset_mode": False}))
    else:
        st.subheader(f"🏢 Parceira: {st.session_state.n}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()
        
        if not df_empresa.
