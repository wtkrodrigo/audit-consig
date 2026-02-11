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
</style>""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""<div class='logo-container'><span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES <span style='font-weight:normal; color:#666; font-size:18px;'>| {titulo}</span></div>
    </div>""", unsafe_allow_html=True)
    st.write("---")

# --- 2. CONEXÃO ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Erro nos Secrets do Supabase."); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. NAVEGAÇÃO ---
menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

# --- MÓDULO FUNCIONÁRIO ---
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")
    
    with st.container():
        st.write("### 🔐 Validação de Identidade")
        st.info("Para sua segurança, informe os dados abaixo para liberar sua auditoria.")
        
        c1, c2 = st.columns(2)
        cpf_in = c1.text_input("CPF (somente números)")
        # Campo de data para evitar erro de digitação
        dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930,1,1), format="DD/MM/YYYY")
        
        # Pedir apenas os 4 últimos dígitos do telefone como segundo fator
        tel_fim_in = st.text_input("Informe os últimos 4 dígitos do seu telefone celular", max_chars=4)
        
        c_clean = "".join(filter(str.isdigit, cpf_in))
    
    if st.button("🔓 ACESSAR AUDITORIA") and c_clean:
        # Busca o registro pelo CPF
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c_clean).execute()
        
        if r.data:
            d = r.data[-1] # Pega o registro mais recente
            
            # --- LÓGICA DE VALIDAÇÃO ---
            # Compara a data de nascimento (convertida para string) e o final do telefone
            valida_data = (str(dt_nasc_in) == str(d.get("data_nascimento", "")))
            valida_tel = str(d.get("telefone", "")).endswith(tel_fim_in)
            
            if valida_data and valida_tel:
                st.success(f"Identidade Confirmada! Bem-vindo(a), {d['nome_funcionario']}")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):,.2f}")
                m2.metric("Banco", d.get('banco_nome', 'N/A'))
                
                status = "✅ CONFORME" if d.get('diferenca', 0) == 0 else "⚠️ DIVERGÊNCIA"
                m3.metric("Status", status)
                
                with st.expander("📊 Detalhamento do Contrato e Parcelas"):
                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.write(f"**Valor do Empréstimo:** R$ {d.get('valor_emprestimo', 0):,.2f}")
                        st.write(f"**ID do Contrato:** {d.get('contrato_id', 'N/A')}")
                    
                    with col_det2:
                        p_pagas = int(d.get('parcelas_pagas', 0))
                        p_total = int(d.get('parcelas_total', 0))
                        st.write(f"**Progresso de Pagamento:** {p_pagas} de {p_total} parcelas")
                        if p_total > 0:
                            prog = min(p_pagas / p_total, 1.0)
                            st.progress(prog, text=f"{int(prog*100)}% concluído")
            else:
                st.error("Dados de validação (Data ou Telefone) não conferem com nossos registros.")
        else:
            st.warning("Nenhum registro encontrado para este CPF.")

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
            else: st.error("Erro de login.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        if st.button("🔄 SINCRONIZAR PLANILHA AGORA"):
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
                st.success("Sincronizado com sucesso!")
            except Exception as e: st.error(f"Erro na sincronização: {e}")
        
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        if res_db.data: st.dataframe(pd.DataFrame(res_db.data), use_container_width=True)

# --- MÓDULO ADMIN ---
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")
    if st.sidebar.text_input("Chave Master", type='password') == st.secrets.get("SENHA_MASTER", "RRB123"):
        with st.form("f_adm"):
            st.subheader("📝 Cadastrar Nova Empresa")
            c1, c2 = st.columns(2); rz = c1.text_input("Razão Social"); cj = c2.text_input("CNPJ")
            lo = c1.text_input("Login Administrativo"); se = c2.text_input("Senha", type='password')
            lk = st.text_input("URL da Planilha CSV")
            if st.form_submit_button("✅ SALVAR"):
                dt = {"nome_empresa": rz, "cnpj": cj, "login": lo, "senha": h(se), "link_planilha": lk}
                sb.table("empresas").insert(dt).execute(); st.success("Empresa cadastrada!")
