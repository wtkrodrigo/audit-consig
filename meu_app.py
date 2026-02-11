import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    # Garante que os segredos existam antes de tentar a conexão
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    else:
        st.error("Configurações do Supabase não encontradas nos Secrets.")
        st.stop()
except Exception as e:
    st.error(f"Erro de conexão com o banco de dados: {e}")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    cpf_in = st.text_input("Digite seu CPF (somente números)")
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        try:
            r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
            if r.data:
                d = r.data[-1]  # Último registro processado
                st.success(f"Bem-vindo, {d['nome_funcionario']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                c2.metric("Banco", d.get('banco_nome', 'N/A'))
                status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                c3.metric("Status", status)
                
                with st.expander("Detalhamento do Empréstimo"):
                    st.write(f"**Valor do Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                    st.write(f"**Contrato:** {d.get('contrato_id', 'N/A')}")
                    st.write(f"**Parcelas Totais:** {d.get('parcelas_total', 0)}")
            else:
                st.warning("Nenhum dado encontrado para este CPF.")
        except Exception as e:
            st.error(f"Erro ao consultar dados: {e}")

# --- MÓDULO EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")
    if 'at' not in st.session_state: 
        st.session_state.at = False
    
    if not st.session_state.at:
        with st.container():
            u = st.text_input("Usuário Corporativo")
            p = st.text_input("Senha", type='password')
            if st.button("ACESSAR PAINEL"):
                try:
                    q = sb.table("empresas").select("*").eq("login", u).execute()
                    if q.data and h(p) == q.data[0]['senha']:
                        st.session_state.at = True
                        st.session_state.n = q.data[0]['nome_empresa']
                        st.session_state.lk = q.data[0].get('link_planilha')
                        st.rerun()
                    else: 
                        st.error("Acesso negado. Usuário ou senha incorretos.")
                except Exception as e:
                    st.error(f"Erro na autenticação: {e}")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.sidebar.button("FINALIZAR SESSÃO"):
            st.session_state.at = False
            st.rerun()
            
        if st.button("🔄 SINCRONIZAR PLANILHA AGORA"):
            try:
                with st.spinner("Processando dados..."):
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    
                    for _, row in df.iterrows():
                        vr = float(pd.to_numeric(row.get('valor_rh', 0), 'coerce') or 0)
                        vb = float(pd.to_numeric(row.get('valor_banco', 0), 'coerce') or 0)
                        
                        payload = {
                            "nome_empresa": st.session_state.n,
                            "cpf": "".join(filter(str.isdigit, str(row['cpf']))),
                            "nome_funcionario": str(row['nome']),
                            "valor_rh": vr,
                            "valor_banco": vb,
                            "valor_emprestimo": float(pd.to_numeric(row.get('valor_emprestimo', 0), 'coerce') or 0),
                            "diferenca": round(vr - vb, 2),
                            "banco_nome": str(row.get('banco', 'N/A')),
                            "contrato_id": str(row.get('contrato', 'N/A')),
                            "parcelas_total": int(pd.to_numeric(row.get('total_parcelas', 0), 'coerce') or 0),
                            "data_processamento": datetime.now().isoformat()
                        }
                        sb.table("resultados_auditoria").upsert(payload).execute()
                    st.success("Sincronização concluída!")
            except Exception as e:
                st.error(f"Erro ao processar planilha: {e}")

        st.divider()
        st.subheader("📊 Relatório de Auditoria")
        
        try:
            res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
            if res_db.data:
                df_res = pd.DataFrame(res_db.data)
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    busca = st.text_input("🔍 Buscar por Nome ou CPF", "")
                with c2:
                    apenas_erros = st.toggle("Mostrar apenas divergências ⚠️")

                if busca:
                    df_res = df_res[df_res['nome_funcionario'].str.contains(busca, case=False) | df_res['cpf'].str.contains(busca)]
                
                if apenas_erros:
                    df_res = df_res[df_res['diferenca'] != 0]

                st.dataframe(df_res, use_container_width=True, hide_index=True)

                csv = df_res.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Relatório (CSV)",
                    data=csv,
                    file_name=f"auditoria_{st.session_state.n}.csv",
                    mime="text/csv",
                )
            else:
                st.info("Nenhum dado disponível para exibição.")
        except Exception as e:
            st.error(f"Erro ao carregar relatório: {e}")

# --- MÓDULO ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    s_mestre = st.secrets.get("SENHA_MASTER", "RRB123")
    check_p = st.sidebar.text_input("Chave Master", type='password')
    
    if check_p == s_mestre:
        with st.container():
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            with st.form("form_cadastro_master"):
                st.subheader("📝 Cadastrar Nova Empresa Parceira")
                c1, c2, c3 = st.columns([2, 1, 1])
                razao = c1.text_input("Razão Social")
                cnpj = c2.text_input("CNPJ")
                plano = c3.selectbox("Tipo de Plano", ["Standard", "Premium", "Enterprise"])
                
                c4, c5, c6 = st.columns([1, 1, 2])
                rep = c4.text_input("Nome do Representante")
                tel = c5.text_input("Telefone de Contato")
                end = c6.text_input("Endereço Completo")
                
                st.divider()
                c7, c8, c9 = st.columns(3)
                log_e = c7.text_input("Login Administrativo")
                sen_e = c8.text_input("Senha de Acesso", type='password')
                link_c = c9.text_input("URL do CSV (Planilha)")
                
                if st.form_submit_button("✅ SALVAR EMPRESA"):
                    if razao and log_e and sen_e:
                        d_save = {
                            "nome_empresa": razao, "cnpj": cnpj, "representante": rep,
                            "telefone": tel, "endereco": end, "plano": plano,
                            "login": log_e, "senha": h(sen_e), "link_planilha": link_c,
                            "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                        }
                        try:
                            sb.table("empresas").insert(d_save).execute()
                            st.success(f"Empresa {razao} cadastrada!")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                    else:
                        st.error("Preencha Razão Social, Login e Senha.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.write("### 📋 Empresas Ativas")
