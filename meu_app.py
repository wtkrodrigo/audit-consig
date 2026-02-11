import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E DESIGN SYSTEM ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

# CSS Avançado para Modernidade
st.markdown("""
<style>
    /* Estilização Geral e Fontes */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Glassmorphism nas métricas */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 20px;
        border-top: 5px solid #002D62;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    [data-testid="stMetric"]:hover { transform: translateY(-5px); border-top: 5px solid #4A90E2; }

    /* Barra Lateral Moderna */
    section[data-testid="stSidebar"] { background-color: #001529; border-right: 1px solid rgba(255,255,255,0.1); }
    .stRadio > div { gap: 10px; }
    
    /* Botões com Gradiente */
    .stButton > button {
        background: linear-gradient(135deg, #002D62 0%, #0056b3 100%);
        color: white; border: none; padding: 10px 24px;
        border-radius: 12px; font-weight: 600; width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover { opacity: 0.9; transform: scale(1.02); }

    /* Logo e Headers */
    .header-container {
        background: linear-gradient(90deg, #002D62 0%, #001529 100%);
        padding: 30px; border-radius: 20px; color: white;
        margin-bottom: 30px; display: flex; align-items: center; gap: 20px;
    }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class="header-container">
        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 15px;">
            <span style="font-size: 40px;">🛡️</span>
        </div>
        <div>
            <div style="font-size: 28px; font-weight: 800; letter-spacing: -1px;">RRB SOLUÇÕES</div>
            <div style="font-size: 16px; opacity: 0.7; font-weight: 400;">{titulo}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA ---
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.warning("⚠️ Configurações de banco de dados não detectadas.")
        st.stop()
except Exception as e:
    st.error(f"❌ Falha crítica: {e}")
    st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

def logout():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# --- 3. BARRA LATERAL (Nova Identidade) ---
with st.sidebar:
    st.markdown("### 🔍 Auditoria Inteligente")
    st.caption("Sistema de Conciliação Bancária")
    st.write("---")
    menu = st.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
    
    if (menu == "🏢 Empresa" and st.session_state.get('at')) or menu == "⚙️ Admin Master":
        st.write("---")
        if st.button("🚪 Sair da Sessão"): logout()

# --- 4. MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Colaborador")
    with st.container():
        st.markdown("#### 🔐 Acesso Seguro")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("🆔 CPF (apenas números)")
        dt_nasc_in = c2.date_input("📅 Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("📞 Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 VALIDAR E ACESSAR AUDITORIA") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                if str(dt_nasc_in) == str(d.get("data_nascimento")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Bem-vindo(a), {d.get('nome_funcionario')}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("💰 Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("🏦 Banco", d.get('banco_nome', 'N/A'))
                    stt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("📊 Status", stt)
                    
                    with st.expander("📝 Detalhes do Contrato", expanded=True):
                        st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f} | **ID:** {d.get('contrato_id', 'N/A')}")
                        pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 1))
                        st.write(f"**Evolução:** {pp} de {pt} parcelas")
                        st.progress(min(pp/max(pt,1), 1.0))
                else: st.error("Dados de validação não conferem.")
            else: st.warning("CPF não localizado.")
        except: st.error("Erro na consulta.")

# --- 5. MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel Corporativo")
    if 'at' not in st.session_state: st.session_state.at = False
    if 'reset_mode' not in st.session_state: st.session_state.reset_mode = False
    
    if not st.session_state.at:
        if not st.session_state.reset_mode:
            st.markdown("#### 🔑 Login Institucional")
            u = st.text_input("👤 Usuário")
            p = st.text_input("🔒 Senha", type='password')
            if st.button("ACESSAR SISTEMA"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Credenciais inválidas.")
            st.button("❓ Esqueci minha senha", on_click=lambda: st.session_state.update({"reset_mode": True}))
        else:
            st.markdown("#### 🔑 Recuperar Credenciais")
            user_reset = st.text_input("👤 Confirme Usuário")
            cnpj_reset = st.text_input("📄 Confirme CNPJ")
            nova_senha = st.text_input("🆕 Nova Senha", type="password")
            if st.button("✅ ATUALIZAR SENHA"):
                check = sb.table("empresas").select("*").eq("login", user_reset).eq("cnpj", cnpj_reset).execute()
                if check.data:
                    sb.table("empresas").update({"senha": h(nova_senha)}).eq("login", user_reset).execute()
                    st.success("Senha atualizada!"); st.session_state.reset_mode = False; st.rerun()
                else: st.error("Validação falhou.")
            st.button("⬅️ Voltar ao Login", on_click=lambda: st.session_state.update({"reset_mode": False}))
    else:
        st.subheader(f"🏢 {st.session_state.n}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        if not df_empresa.empty:
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("👥 Total Colaboradores", len(df_empresa))
            c_m2.metric("✔️ Conformes", len(df_empresa[df_empresa['diferenca'] == 0]))
            divs = len(df_empresa[df_empresa['diferenca'] != 0])
            c_m3.metric("🚨 Divergentes", divs, delta=f"{divs} erros", delta_color="inverse")
        
        st.divider()
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        with c_act1:
            if st.button("🔄 SINCRONIZAR BASE CSV"):
                try:
                    with st.spinner("Conectando à nuvem..."):
                        df = pd.read_csv(st.session_state.lk)
                        df.columns = df.columns.str.strip().str.lower()
                        payloads = []
                        for _, r in df.iterrows():
                            vr = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0)
                            vb = float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                            payloads.append({
                                "nome_empresa": st.session_state.n, 
                                "cpf": "".join(filter(str.isdigit, str(r.get('cpf', "")))),
                                "nome_funcionario": str(r.get('nome', 'N/A')), 
                                "valor_rh": vr, "valor_banco": vb,
                                "valor_emprestimo": float(pd.to_numeric(r.get('valor_emprestimo', 0), 'coerce') or 0),
                                "diferenca": round(vr - vb, 2), "banco_nome": str(r.get('banco', 'N/A')),
                                "contrato_id": str(r.get('contrato', 'N/A')),
                                "parcelas_total": int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0),
                                "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas', 0), 'coerce') or 0),
                                "data_nascimento": str(r.get('data_nascimento', '')),
                                "telefone": "".join(filter(str.isdigit, str(r.get('telefone', "")))),
                                "data_processamento": datetime.now().isoformat()
                            })
                        if payloads:
                            sb.table("resultados_auditoria").upsert(payloads, on_conflict="cpf, contrato_id").execute()
                            st.toast("Dados sincronizados com sucesso!"); st.rerun()
                except Exception as e: st.error(f"Erro na conexão: {e}")

        with c_act2:
            if not df_empresa.empty:
                st.download_button("📥 EXPORTAR RELATÓRIO", df_empresa.to_csv(index=False).encode('utf-8'), "auditoria_rrb.csv")

        st.markdown("#### 📑 Visão Detalhada")
        busca = st.text_input("🔍 Localizar por Nome ou CPF")
        filtro = st.radio("Filtrar por Status:", ["Todos", "✅ Conformes", "⚠️ Divergentes"], horizontal=True)

        if not df_empresa.empty:
            df_f = df_empresa.copy()
            if filtro == "✅ Conformes": df_f = df_f[df_f['diferenca'] == 0]
            elif filtro == "⚠️ Divergentes": df_f = df_f[df_f['diferenca'] != 0]
            if busca: df_f = df_f[df_f['nome_funcionario'].str.contains(busca, case=False, na=False) | df_f['cpf'].str.contains(busca, na=False)]
            st.dataframe(df_f, use_container_width=True, hide_index=True)

# --- 6. ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Gestão do Sistema")
    if st.sidebar.text_input("🔐 Chave Mestra", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            st.markdown("#### 📝 Cadastro de Nova Parceira")
            c1, c2, c3 = st.columns([2, 1, 1])
            razao, cnpj, plano = c1.text_input("🏢 Razão Social"), c2.text_input("📄 CNPJ"), c3.selectbox("💎 Plano", ["Standard", "Premium", "Enterprise"])
            
            c4, c5, c6 = st.columns([1, 1, 2])
            rep, tel, end = c4.text_input("👤 Representante"), c5.text_input("📞 Telefone"), c6.text_input("📍 Endereço Completo")
            
            st.divider()
            c7, c8, c9 = st.columns(3)
            lo, se, lk = c7.text_input("👤 Login Admin"), c8.text_input("🔒 Senha", type='password'), c9.text_input("🔗 Link Planilha (CSV)")
            
            if st.form_submit_button("🚀 FINALIZAR E ATIVAR EMPRESA"):
                if razao and lo and se:
                    dt = {
                        "nome_empresa": razao, "cnpj": cnpj, "representante": rep, "telefone": tel, "endereco": end, 
                        "plano": plano, "login": lo, "senha": h(se), "link_planilha": lk,
                        "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    try:
                        sb.table("empresas").insert(dt).execute()
                        st.success(f"Empresa {razao} ativada
