import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO (ESCUDO E LOGO) ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""<style>
    .main { background-color: #f9f9f9; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; border-top: 4px solid #002D62; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    .admin-card { background: white; padding: 30px; border-radius: 15px; border: 1px solid #ddd; }
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO SUPABASE ---
try:
    # Busca as credenciais de forma segura nos Secrets do Streamlit
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Erro crítico de conexão: Verifique as chaves no painel do Streamlit.")
    st.stop()

def h(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO LATERAL ---
st.sidebar.markdown("### 📋 MENU DE ACESSO")
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO 1: PORTAL DO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    cpf_in = st.text_input("Digite seu CPF (apenas números)")
    c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("CONSULTAR AUDITORIA") and c_clean:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        if r.data:
            # Pega sempre o registro mais recente (última auditoria)
            d = r.data[-1]
            st.success(f"Bem-vindo(a), {d.get('nome_funcionario', 'Usuário')}")
            
            # Métricas principais
            c1, c2, c3 = st.columns(3)
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
            c2.metric("Instituição Bancária", d.get('banco_nome', 'N/A'))
            status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
            c3.metric("Status Auditoria", status)
            
            # Detalhamento de Parcelas (Novidade)
            total = int(d.get('parcelas_total', 0))
            pagas = int(d.get('parcelas_pagas', 0))
            restantes = max(0, total - pagas)
            
            with st.expander("📊 Detalhamento do Empréstimo e Parcelas", expanded=True):
                col_a, col_b = st.columns(2)
                col_a.write(f"**Valor Original:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                col_a.write(f"**Contrato ID:** {d.get('contrato_id', 'N/A')}")
                col_b.write(f"**Parcelas Pagas:** {pagas}")
                col_b.write(f"**Parcelas Restantes:** {restantes}")
                col_b.write(f"**Duração Total:** {total} meses")
                
                if total > 0:
                    progresso = min(1.0, pagas / total)
                    st.progress(progresso)
                    st.caption(f"Progresso de Quitação: {progresso*100:.1f}% completo")
        else:
            st.warning("Nenhum dado de auditoria localizado para este CPF.")

# --- MÓDULO 2: PAINEL DA EMPRESA ---
elif menu == "🏢 Empresa":
    render_header("Painel Corporativo")
    if 'at' not in st.session_state: 
        st.session_state.at = False
    
    if not st.session_state.at:
        with st.container():
            st.info("Acesse com suas credenciais de parceiro RRB.")
            u = st.text_input("Usuário Corporativo")
            p = st.text_input("Senha", type='password')
            if st.button("ACESSAR PAINEL"):
                q = sb.table("empresas").select("*").eq("login", u).execute()
                if q.data and h(p) == q.data[0]['senha']:
                    st.session_state.at = True
                    st.session_state.n = q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: 
                    st.error("Credenciais inválidas ou empresa não cadastrada.")
    else:
        st.subheader(f"Gestão Corporativa: {st.session_state.n}")
        if st.sidebar.button("LOGOUT (SAIR)"):
            st.session_state.at = False
            st.rerun()
            
        if st.button("🔄 SINCRONIZAR DADOS DA PLANILHA"):
            try:
                # Carrega o CSV do Google Sheets
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                
                for _, r in df.iterrows():
                    vr = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0)
                    vb = float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                    
                    payload = {
                        "nome_empresa": st.session_state.n,
                        "cpf": "".join(filter(str.isdigit, str(r['cpf']))),
                        "nome_funcionario": str(r['nome']),
                        "valor_rh": vr,
                        "valor_banco": vb,
                        "valor_emprestimo": float(pd.to_numeric(r.get('valor_emprestimo', 0), 'coerce') or 0),
                        "diferenca": round(vr - vb, 2),
                        "banco_nome": str(r.get('banco', 'N/A')),
                        "contrato_id": str(r.get('contrato', 'N/A')),
                        "parcelas_total": int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0),
                        "parcelas_pagas": int(pd.to_numeric(r.get('parcelas_pagas', 0), 'coerce') or 0),
                        "data_processamento": datetime.now().isoformat()
                    }
                    # Upsert evita duplicação (CPF + Contrato)
                    sb.table("resultados_auditoria").upsert(payload, on_conflict="cpf,contrato_id").execute()
                st.success("Base de dados sincronizada com sucesso!")
            except Exception as e: 
                st.error(f"Erro na sincronização: Verifique o formato da planilha. Detalhes: {e}")
        
        # Exibe a tabela atualizada para a empresa
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        if res_db.data:
            df_final = pd.DataFrame(res_db.data)
            # Seleciona apenas colunas relevantes para a empresa
            cols = ['nome_funcionario', 'cpf', 'contrato_id', 'parcelas_pagas', 'parcelas_total', 'diferenca']
            st.dataframe(df_final[cols], use_container_width=True)

# --- MÓDULO 3: ADMIN MASTER ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    s_mestre = st.secrets.get("SENHA_MASTER", "RRB123")
    check_p = st.sidebar.text_input("Chave Master de Acesso", type='password')
    
    if check_p == s_mestre:
        with st.container():
            st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
            with st.form("form_cadastro_master"):
                st.subheader("📝 Cadastrar Nova Empresa Parceira")
                c1, c2, c3 = st.columns([2, 1, 1])
                razao = c1.text_input("Razão Social da Empresa")
                cnpj = c2.text_input("CNPJ")
                plano = c3.selectbox("Tipo de Plano", ["Standard", "Premium", "Enterprise"])
                
                c4, c5, c6 = st.columns([1, 1, 2])
                rep = c4.text_input("Responsável Técnico/Legal")
                tel = c5.text_input("WhatsApp de Contato")
                end = c6.text_input("Endereço da Sede")
                
                st.divider()
                c7, c8, c9 = st.columns(3)
                log_e = c7.text_input("Login Administrativo")
                sen_e = c8.text_input("Senha de Acesso", type='password')
                link_c = c9.text_input("Link da Planilha (CSV)")
                
                if st.form_submit_button("✅ SALVAR EMPRESA NO SISTEMA"):
                    if razao and log_e and sen_e:
                        d_save = {
                            "nome_empresa": razao, "cnpj": cnpj, "representante": rep,
                            "telefone": tel, "endereco": end, "plano": plano,
                            "login": log_e, "senha": h(sen_e), "link_planilha": link_c,
                            "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
                        }
                        try:
                            sb.table("empresas").insert(d_save).execute()
                            st.success(f"Empresa '{razao}' integrada com sucesso!")
                        except Exception as e: 
                            st.error(f"Erro ao salvar no banco: {e}")
                    else: 
                        st.error("Campos obrigatórios: Razão Social, Login e Senha.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Listagem de empresas já cadastradas
            st.write("### 📋 Portfólio de Empresas Ativas")
            lst = sb.table("empresas").select("nome_empresa, representante, plano").execute()
            if lst.data: 
                st.table(pd.DataFrame(lst.data))
    elif check_p != "": 
        st.error("Chave Master Incorreta.")
    else: 
        st.info("Insira a Chave Master na barra lateral para liberar as ferramentas.")
