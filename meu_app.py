import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")

# CSS para Elegância e Modernidade
st.markdown("""<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; width: 100%; }
    .logo-text { font-size: 24px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

# Função para exibir o Logo em todas as abas
def mostrar_logo():
    st.markdown("<div class='logo-text'>🛡️ RRB SOLUÇÕES</div>", unsafe_allow_html=True)
    st.caption("Auditoria Inteligente e Transparência")
    st.write("---")

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro nas Credenciais"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAVEGAÇÃO ---
st.sidebar.title("MENU RRB")
m = st.sidebar.radio("Ir para:", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin"])

# --- 1. MÓDULO FUNCIONÁRIO ---
if m == "👤 Funcionário":
    mostrar_logo()
    st.subheader("🔎 Minha Auditoria")
    cpf = st.text_input("Digite seu CPF")
    c = "".join(filter(str.isdigit, cpf))
    
    if st.button("CONSULTAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            
            # Lógica de Parcelas
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg = len(hist)
            v_tp = d.get('parcelas_total')
            tt = int(float(v_tp)) if v_tp and str(v_tp).lower() != 'nan' else 0
            
            # Layout de Dados
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Valor Mensal", f"R$ {d.get('valor_rh', 0):.2f}")
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Alerta")
            
            st.info(f"🏦 Banco: {d.get('banco_nome')} | 📄 Contrato: {ct}")
            if tt > 0: st.progress(min(1.0, pg/tt))
        else:
            st.warning("CPF não localizado no sistema.")

# --- 2. MÓDULO EMPRESA ---
elif m == "🏢 Empresa":
    mostrar_logo()
    if 'at' not in st.session_state: st.session_state.at = False
    
    if not st.session_state.at:
        with st.columns([1,1.5,1])[1]:
            st.subheader("🔐 Painel da Empresa")
            u_in = st.text_input("Usuário")
            p_in = st.text_input("Senha", type='password')
            if st.button("ACESSAR"):
                q = sb.table("empresas").select("*").eq("login", u_in).execute()
                if q.data and h(p_in) == q.data[0]['senha']:
                    st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                    st.session_state.lk = q.data[0].get('link_planilha')
                    st.rerun()
                else: st.error("Dados incorretos.")
    else:
        col_t, col_s = st.columns([4, 1])
        col_t.subheader(f"Gestão Corporativa: {st.session_state.n}")
        if col_s.button("SAIR"): st.session_state.at = False; st.rerun()

        with st.expander("📥 Sincronização de Dados"):
            if st.button("SINCRONIZAR FOLHA ATUAL"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = pd.to_numeric(r['valor_rh'], 'coerce')
                        vb = pd.to_numeric(r['valor_banco'], 'coerce')
                        tp = pd.to_numeric(r['total_parcelas'], 'coerce')
                        vr, vb = float(vr or 0), float(vb or 0)
                        tp = int(tp or 0)
                        
                        pld = {"nome_empresa":st.session_state.n,"cpf":str(r['cpf']),
                        "nome_funcionario":str(r['nome']),"valor_rh":vr,"valor_banco":vb,
                        "diferenca":vr-vb,"banco_nome":str(r.get('banco','N/A')),
                        "contrato_id":str(r.get('contrato','N/A')),"parcelas_total":tp,
                        "data_processamento":datetime.now().isoformat()}
                        sb.table("resultados_auditoria").insert(pld).execute()
                    st.success("✅ Dados processados!")
                except Exception as e: st.error(f"Erro: {e}")

        st.write("📋 **Relatório de Auditoria Detalhado**")
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).execute()
        
        if res.data:
            f_df = pd.DataFrame(res.data)
            v_list = []
            for i, row in f_df.head(25).iterrows():
                # Cálculo de parcelas robusto
                p_pg = len(f_df[f_df['contrato_id'] == row['contrato_id']])
                raw_tp = row['parcelas_total']
                t_parc = int(float(raw_tp)) if raw_tp and str(raw_tp).lower() != 'nan' else 0
                
                v_list.append({
                    "Funcionário": row['nome_funcionario'],
                    "Banco": row['banco_nome'],
                    "Contrato": row['contrato_id'],
                    "V. RH": f"R$ {row['valor_rh']:.2f}",
                    "Pagas": p_pg,
                    "Faltam": max(0, t_parc - p_pg),
                    "Diferença": f"R$ {row['diferenca']:.2f}"
                })
            st.table(pd.DataFrame(v_list))

# --- 3. MÓDULO ADMIN ---
elif m == "⚙️ Admin":
    mostrar_logo()
    st.subheader("⚙️ Central de Controle")
    pw = st.text_input("Senha Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cadastro_final"):
            st.markdown("#### 🏢 Identificação")
            c1, c2 = st.columns(2)
            rs = c1.text_input("Razão Social")
            cj = c2.text_input("CNPJ")
            
            st.markdown("#### 📞 Contato")
            c3, c4 = st.columns(2)
            rp = c3.text_input("Representante")
            tl = c4.text_input("Telefone")
            en = st.text_input("Endereço")
            
            st.markdown("#### 💎 Plano e Acesso")
            plano = st.selectbox("Tipo de Plano", ["Prata", "Ouro", "Black"])
            c5, c6 = st.columns(2)
            us = c5.text_input("Login")
            sn = c5.text_input("Senha", type='password')
            lk = c6.text_input("Link da Planilha (CSV)")
            
            if st.form_submit_button("CADASTRAR CLIENTE"):
                v = (datetime.now()+timedelta(30)).isoformat()
                di = {"nome_empresa": rs, "cnpj": cj, "representante": rp,
                "telefone": tl, "endereco": en, "login": us, "senha": h(sn),
                "data_expiracao": v, "link_planilha": lk, "plano": plano}
                sb.table("empresas").insert(di).execute()
                st.success(f"Empresa cadastrada no Plano {plano}!")
