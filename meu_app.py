import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #eee; margin-bottom: 20px; }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>""", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro nos Secrets."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO (VALIDAÇÃO TRIPLA) ---
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
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            d = r.data[-1]
            if str(dt_nasc_in) == str(d.get("data_nascimento", "")) and str(d.get("telefone", "")).endswith(tel_fim_in):
                st.success(f"Bem-vindo, {d['nome_funcionario']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                m2.metric("Banco", d.get('banco_nome', 'N/A'))
                m3.metric("Status", "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA")
                with st.expander("📊 Detalhes do Contrato"):
                    st.write(f"**Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f} | **ID:** {d.get('contrato_id', 'N/A')}")
                    pp, pt = int(d.get('parcelas_pagas', 0)), int(d.get('parcelas_total', 0))
                    st.write(f"**Parcelas:** {pp} de {pt}")
                    if pt > 0: st.progress(min(pp/pt, 1.0))
            else: st.error("Dados de validação incorretos.")
        else: st.warning("CPF não localizado.")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u = st.text_input("Usuário"); p = st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u).execute()
            if q.data and h(p) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha'); st.rerun()
            else: st.error("Login inválido.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.button("🔄 SINCRONIZAR AGORA"):
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
                st.success("Sincronizado!")
            except Exception as e: st.error(f"Erro: {e}")
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        if res_db.data: st.dataframe(pd.DataFrame(res_db.data), use_container_width=True)

# --- MÓDULO ADMIN MASTER (RESTAURADO E AMPLIADO) ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        
        # 1. FORMULÁRIO DE CADASTRO
        with st.form("f_adm_master"):
            st.subheader("📝 Cadastrar Nova Empresa Parceira")
            c1, c2, c3 = st.columns([2, 1, 1])
            razao = c1.text_input("Razão Social")
            cnpj = c2.text_input("CNPJ")
            plano = c3.selectbox("Plano", ["Standard", "Premium", "Enterprise"])
            
            c4, c5, c6 = st.columns([1, 1, 2])
            rep = c4.text_input("Representante")
            tel = c5.text_input("Telefone")
            end = c6.text_input("Endereço Completo")
            
            st.divider()
            c7, c8, c9 = st.columns(3)
            lo = c7.text_input("Login Administrativo")
            se = c8.text_input("Senha", type='password')
            lk = c9.text_input("URL Planilha (CSV)")
            
            if st.form_submit_button("✅ SALVAR EMPRESA"):
                if razao and lo and se:
                    dt = {
                        "nome_empresa": razao, "cnpj": cnpj, "representante": rep,
                        "telefone": tel, "endereco": end, "plano": plano,
                        "login": lo, "senha": h(se), "link_planilha": lk,
                        "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    try:
                        sb.table("empresas").insert(dt).execute()
                        st.success(f"Empresa {razao} cadastrada!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
                else: st.error("Preencha Razão, Login e Senha.")

        # 2. LISTA DE EMPRESAS CADASTRADAS
        st.write("---")
        st.subheader("📋 Empresas Ativas no Sistema")
        try:
            empresas = sb.table("empresas").select("nome_empresa, cnpj, representante, plano, data_expiracao").execute()
            if empresas.data:
                df_emp = pd.DataFrame(empresas.data)
                df_emp.columns = ["Nome da Empresa", "CNPJ", "Representante", "Plano", "Expiração"]
                st.dataframe(df_emp, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma empresa cadastrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar lista: {e}")
