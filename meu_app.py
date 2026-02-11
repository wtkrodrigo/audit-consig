import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- ESTILO E LOGO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .logo { font-size: 26px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

def logo():
    st.markdown("<div class='logo'>🛡️ RRB SOLUÇÕES</div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nos Secrets (URL/KEY do Supabase)"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.title("PAINEL RRB")
m = st.sidebar.radio("Navegação", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    logo()
    cpf_input = st.text_input("Digite seu CPF")
    c = "".join(filter(str.isdigit, cpf_input))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            
            c1, c2, c3 = st.columns(3)
            # Calculando progresso simples baseado no histórico de registros se houver
            pg = len([x for x in r.data if x.get('contrato_id') == d.get('contrato_id')])
            tt = int(d['parcelas_total']) if d.get('parcelas_total') else 0
            
            c1.metric("Parcelas", f"{pg}/{tt}")
            c1.metric("Mensalidade RH", f"R$ {d.get('valor_rh', 0):.2f}")
            c2.metric("Banco", d.get('banco_nome', 'N/A'))
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Erro")
            
            if tt > 0: 
                st.progress(min(1.0, pg/tt))
        else:
            st.warning("CPF não encontrado na base de auditoria.")

# --- 2. MÓDULO EMPRESA ---
elif m == "🏢 Empresa":
    logo()
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        u_i, p_i = st.text_input("Usuário"), st.text_input("Senha", type='password')
        if st.button("ACESSAR"):
            q = sb.table("empresas").select("*").eq("login", u_i).execute()
            if q.data and h(p_i) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
            else:
                st.error("Credenciais inválidas")
    else:
        st.subheader(f"🏢 Gestão: {st.session_state.n}")
        if st.sidebar.button("SAIR"): 
            st.session_state.at = False
            st.rerun()
        
        with st.expander("📥 Sincronização de Dados"):
            if st.button("SINCRONIZAR AGORA"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    
                    for _, r in df.iterrows():
                        vr = float(pd.to_numeric(r.get('valor_rh', 0), 'coerce') or 0)
                        vb = float(pd.to_numeric(r.get('valor_banco', 0), 'coerce') or 0)
                        ve = float(pd.to_numeric(r.get('valor_emprestimo', 0), 'coerce') or 0)
                        tp = int(pd.to_numeric(r.get('total_parcelas', 0), 'coerce') or 0)
                        clean_cpf = "".join(filter(str.isdigit, str(r['cpf'])))
                        
                        p = {
                            "nome_empresa": st.session_state.n,
                            "cpf": clean_cpf,
                            "nome_funcionario": str(r['nome']),
                            "valor_rh": vr,
                            "valor_banco": vb,
                            "valor_emprestimo": ve,
                            "diferenca": round(vr - vb, 2),
                            "banco_nome": str(r.get('banco', 'N/A')),
                            "contrato_id": str(r.get('contrato', 'N/A')),
                            "parcelas_total": tp,
                            "data_processamento": datetime.now().isoformat()
                        }
                        # Usa upsert para não duplicar dados identicos (CPF + Contrato)
                        sb.table("resultados_auditoria").upsert(p).execute()
                        
                    st.success("Sincronização realizada com sucesso!")
                except Exception as e: 
                    st.error(f"Erro: {e}")

        # VISUALIZAÇÃO
        res = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        if res.data:
            f_df = pd.DataFrame(res.data)
            v_l = []
            for ct in f_df['contrato_id'].unique():
                cd = f_df[f_df['contrato_id'] == ct]
                rw = cd.iloc[-1]
                v_l.append({
                    "Funcionário": rw['nome_funcionario'],
                    "CPF": rw['cpf'],
                    "Banco": rw['banco_nome'],
                    "Desc. Empresa": f"R$ {rw['valor_rh']:.2f}",
                    "Parc. Banco": f"R$ {rw['valor_banco']:.2f}",
                    "Diferença": f"R$ {rw['diferenca']:.2f}",
                    "Status": "✅ OK" if rw['diferenca'] == 0 else "⚠️ Erro"
                })
            st.table(pd.DataFrame(v_l))

# --- 3. MÓDULO ADMIN ---
elif m == "⚙️ Admin":
    logo()
    if st.text_input("Master", type='password') == st.secrets.get("SENHA_MASTER"):
        with st.form("cad_emp"):
            c1, c2 = st.columns(2)
            rs, cj = c1.text_input("Razão Social"), c2.text_input("CNPJ")
            us, sn = c1.text_input("Usuário"), c2.text_input("Senha", type='password')
            lk = st.text_input("Link CSV")
            if st.form_submit_button("CADASTRAR"):
                v = (datetime.now() + timedelta(30)).isoformat()
                d = {"nome_empresa": rs, "cnpj": cj, "login": us, "senha": h(sn), 
                     "link_planilha": lk, "data_expiracao": v}
                sb.table("empresas").insert(d).execute()
                st.success("Empresa cadastrada!")
