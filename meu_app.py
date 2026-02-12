import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta, date

# ============================================================
# 0) CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

# ============================================================
# 1) CSS PREMIUM (Saneado)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp {
    background: radial-gradient(1200px 800px at 12% 10%, rgba(74,144,226,0.16), transparent 60%),
                linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,248,255,1));
}
.rrb-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.5rem; border-radius: 18px;
    background: rgba(255,255,255,0.7); border: 1px solid rgba(0,45,98,0.1);
    backdrop-filter: blur(12px); margin-bottom: 2rem;
}
.rrb-title { font-size: 24px; font-weight: 900; color: #002D62; margin: 0; }
.rrb-glass {
    background: rgba(255,255,255,0.6); border: 1px solid rgba(0,45,98,0.1);
    border-radius: 18px; padding: 25px; backdrop-filter: blur(10px);
}
[data-testid="stMetric"] {
    background: white; border-radius: 15px; padding: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2) FUNÇÕES UTILITÁRIAS
# ============================================================
def sha256_hex(p: str) -> str:
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()

def digits_only(s: str) -> str:
    return "".join(filter(str.isdigit, str(s or "")))

def normalize_date_yyyy_mm_dd(value) -> str:
    if not value: return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    try:
        if "T" in s: return s.split("T")[0]
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except:
        return s

def logout():
    st.session_state.clear()
    st.rerun()

# ============================================================
# 3) CONEXÃO E SEGURANÇA
# ============================================================
if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
    st.error("Configuração incompleta: SUPABASE_URL ou SUPABASE_KEY não encontrados nos Secrets.")
    st.stop()

sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

if "authenticated" not in st.session_state:
    st.session_state.update({"authenticated": False, "empresa_nome": None, "empresa_csv_url": None})

# ============================================================
# 4) INTERFACE
# ============================================================
menu = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

def render_header(titulo):
    st.markdown(f'<div class="rrb-header"><div class="rrb-title">RRB Soluções <small style="font-size:14px; font-weight:400;">| {titulo}</small></div></div>', unsafe_allow_html=True)

# --- PORTAL FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Consulta de Auditoria")
    with st.container():
        st.markdown('<div class="rrb-glass">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (apenas números)", max_chars=11)
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=date(1930, 1, 1), format="DD/MM/YYYY")
        tel_fim = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("CONSULTAR AGORA", use_container_width=True):
        res = sb.table("resultados_auditoria").select("*").eq("cpf", digits_only(cpf_in)).order("data_processamento", desc=True).limit(1).execute()
        if res.data:
            d = res.data[0]
            valid_nasc = (normalize_date_yyyy_mm_dd(d.get("data_nascimento")) == normalize_date_yyyy_mm_dd(dt_nasc_in))
            valid_tel = digits_only(d.get("telefone", "")).endswith(tel_fim)
            
            if valid_nasc and valid_tel:
                st.success(f"Dados validados para: {d.get('nome_funcionario')}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Valor em Folha (RH)", f"R$ {float(d.get('valor_rh', 0)):,.2f}")
                m2.metric("Valor Contrato", f"R$ {float(d.get('valor_banco', 0)):,.2f}")
                dif = float(d.get("diferenca", 0))
                m3.metric("Status", "CONFORME" if abs(dif) < 0.05 else "DIVERGENTE", delta=f"R$ {dif:,.2f}" if dif != 0 else None, delta_color="inverse")
            else:
                st.error("Dados de confirmação inválidos.")
        else:
            st.warning("Nenhum registro encontrado para este CPF.")

# --- PORTAL EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel Administrativo")
    if not st.session_state["authenticated"]:
        with st.form("login_empresa"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Painel"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and sha256_hex(p) == q.data[0].get("senha"):
                    st.session_state.update({"authenticated": True, "empresa_nome": q.data[0].get("nome_empresa"), "empresa_csv_url": q.data[0].get("link_planilha")})
                    st.rerun()
                else:
                    st.error("Login ou senha incorretos.")
    else:
        st.sidebar.button("Sair do Sistema", on_click=logout)
        st.subheader(f"Empresa: {st.session_state['empresa_nome']}")
        
        if st.button("🔄 SINCRONIZAR DADOS (CSV)"):
            try:
                df = pd.read_csv(st.session_state["empresa_csv_url"])
                df.columns = df.columns.str.strip().str.lower()
                payloads = []
                for _, r in df.iterrows():
                    v_rh = float(str(r.get('valor_rh', 0)).replace(',','.'))
                    v_bn = float(str(r.get('valor_banco', 0)).replace(',','.'))
                    payloads.append({
                        "nome_empresa": st.session_state["empresa_nome"],
                        "cpf": digits_only(str(r.get("cpf"))),
                        "nome_funcionario": str(r.get("nome", "Não informado")),
                        "valor_rh": v_rh, "valor_banco": v_bn, "diferenca": round(v_rh - v_bn, 2),
                        "banco_nome": str(r.get("banco", "N/A")), "contrato_id": str(r.get("contrato", "0")),
                        "data_nascimento": normalize_date_yyyy_mm_dd(r.get("data_nascimento")),
                        "telefone": digits_only(str(r.get("telefone"))),
                        "data_processamento": datetime.now().isoformat()
                    })
                sb.table("resultados_auditoria").upsert(payloads, on_conflict="nome_empresa,cpf,contrato_id").execute()
                st.success("Base de dados atualizada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao processar CSV: {e}")

# --- ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações do Sistema")
    master_pass = st.sidebar.text_input("Chave Mestre", type="password")
    if master_pass == st.secrets.get("SENHA_MASTER"):
        with st.form("add_empresa"):
            st.write("Registrar Nova Empresa Parceira")
            f1, f2 = st.columns(2)
            nome_e = f1.text_input("Razão Social")
            login_e = f2.text_input("Usuário Admin")
            senha_e = f1.text_input("Senha", type="password")
            url_e = f2.text_input("Link Público CSV")
            if st.form_submit_button("Salvar Empresa"):
                sb.table("empresas").insert({"nome_empresa": nome_e, "login": login_e, "senha": sha256_hex(senha_e), "link_planilha": url_e}).execute()
                st.success("Empresa adicionada!")
    else:
        st.info("Aguardando Chave Mestre...")
