import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO (Restaurado Integralmente) ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.05);
        padding: 15px 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    @media (prefers-color-scheme: dark) { .logo-text { color: #4A90E2; } }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:gray; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

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
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. NAVEGAÇÃO LATERAL (Ícones Adicionados) ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if (menu == "🏢 Empresa" and st.session_state.get('at')) or menu == "⚙️ Admin Master":
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Sair da Sessão"):
        logout()

# --- 4. MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    with st.container():
        st.info("🔐 Informe seus dados para liberar a consulta.")
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]
                # Validação de Segurança
                if str(dt_nasc_in) == str(d.get("data_nascimento")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                    st.success(f"Bem-vindo, {d.get('nome_funcionario', 'Funcionário')}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                    m2.metric("Banco", d.get('banco_nome', 'N/A'))
                    stt = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                    m3.metric("Status", stt)
                    with st.expander("📊 Detalhes do Contrato"):
                        st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f} | **ID:** {d.get('contrato_id', 'N/A')}")
                        pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                        st.write(f"**Parcelas:** {pp} de {pt}")
                        if pt > 0: st.progress(min(pp/pt, 1.0))
                else: st.error("Dados de validação incorretos.")
            else: st.warning("CPF não localizado.")
        except: st.error("Erro na consulta.")

# --- 5. MÓDULO EMPRESA (Toda a lógica original restaurada) ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    if 'reset_mode' not in st.session_state: st.session_state.reset_mode = False
    
    if not st.session_state.at:
        if not st.session_state.reset_mode:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type='password')
            if st.button("ACESSAR", use_container_width=True):
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
            user_reset = st.text_input("Confirme Usuário")
            cnpj_reset = st.text_input("Confirme CNPJ")
            nova_senha = st.text_input("Nova Senha", type="password")
            if st.button("ATUALIZAR"):
                check = sb.table("empresas").select("*").eq("login", user_reset).eq("cnpj", cnpj_reset).execute()
                if check.data:
                    sb.table("empresas").update({"senha": h(nova_senha)}).eq("login", user_reset).execute()
                    st.success("Sucesso!"); st.session_state.reset_mode = False; st.rerun()
                else: st.error("Dados incorretos.")
            if st.button("Voltar"): st.session_state.reset_mode = False; st.rerun()
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_empresa = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        if not df_empresa.empty:
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Total Base", len(df_empresa))
            c_m2.metric("Conformes", len(df_empresa[df_empresa['diferenca'] == 0]))
            divs = len(df_empresa[df_empresa['diferenca'] != 0])
            c_m3.metric("Divergentes", divs, delta=f"{divs} erros" if divs > 0 else None, delta_color="inverse")
        
        st.divider()
        c_act1, c_act2, _ = st.columns([1, 1, 2])
        with c_act1:
            if st.button("🔄 SINCRONIZAR CSV", use_container_width=True):
                try:
                    with st.spinner("Sincronizando..."):
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
                            st.toast("Sucesso!"); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

        with c_act2:
            if not df_empresa.empty:
                st.download_button("📥 EXPORTAR", df_empresa.to_csv(index=False).encode('utf-8'), "auditoria.csv", use_container_width=True)

        busca = st.text_input("🔍 Pesquisar Nome ou CPF")
        filtro = st.radio("Filtro de Status:", ["Todos", "✅ Conformes", "⚠️ Divergentes"], horizontal=True)

        if not df_empresa.empty:
            df_f = df_empresa.copy()
            if filtro == "✅ Conformes": df_f = df_f[df_f['diferenca'] == 0]
            elif filtro == "⚠️ Divergentes": df_f = df_f[df_f['diferenca'] != 0]
            if busca: df_f = df_f[df_f['nome_funcionario'].str.contains(busca, case=False, na=False) | df_f['cpf'].str.contains(busca, na=False)]
            
            st.dataframe(df_f, use_container_width=True, hide_index=True)

# --- 6. ADMIN MASTER (Restauração dos Campos de Cadastro) ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            st.subheader("📝 Cadastrar Nova Empresa Parceira")
            c1, c2, c3 = st.columns([2, 1, 1])
            razao, cnpj, plano = c1.text_input("Razão Social"), c2.text_input("CNPJ"), c3.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
            
            c4, c5, c6 = st.columns([1, 1, 2])
            rep, tel, end = c4.text_input("Representante"), c5.text_input("Telefone"), c6.text_input("Endereço Completo")
            
            st.divider()
            c7, c8, c9 = st.columns(3)
            lo, se, lk = c7.text_input("Login Administrativo"), c8.text_input("Senha", type='password'), c9.text_input("URL (CSV)")
            
            if st.form_submit_button("✅ SALVAR EMPRESA"):
                if razao and lo and se:
                    dt = {
                        "nome_empresa": razao, "cnpj": cnpj, "representante": rep, "telefone": tel, "endereco": end, 
                        "plano": plano, "login": lo, "senha": h(se), "link_planilha": lk,
                        "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    try:
                        sb.table("empresas").insert(dt).execute()
                        st.success("Empresa cadastrada!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
        
        st.write("---")
        st.subheader("🏢 Empresas Ativas")
        try:
            em = sb.table("empresas").select("*").execute()
            if em.data:
                st.dataframe(pd.DataFrame(em.data)[["nome_empresa", "cnpj", "representante", "plano"]], use_container_width=True, hide_index=True)
        except: pass
