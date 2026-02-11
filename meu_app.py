import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- ESTILO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; }
</style>""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.title("🛡️ RRB CORPORATE")
m = st.sidebar.radio("Menu", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# --- 1. FUNCIONÁRIO ---
if m == "👤 Func":
    st.subheader("🔎 Consulta de Transparência")
    cpf = st.text_input("CPF")
    c = "".join(filter(str.isdigit, cpf))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg = len(hist)
            # Solução para o erro NaN
            v_tp = d.get('parcelas_total')
            tt = int(float(v_tp)) if v_tp and str(v_tp).lower() != 'nan' else 0
            
            st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Banco", d.get('banco_nome'))
            c3.metric("Status", "OK" if d['diferenca']==0 else "Erro")
            if tt > 0: st.progress(min(1.0, pg/tt))

# --- 2. EMPRESA ---
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_in, p_in = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("ENTRAR"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha')
                st.rerun()
    else:
        st.subheader(f"🏢 {st.session_state.n}")
        if st.sidebar.button("SAIR"): st.session_state.at = False; st.rerun()
        with st.expander("📥 Sincronizar Folha"):
            if st.button("EXECUTAR"):
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
                    st.success("Sincronizado!")
                except Exception as e: st.error(f"Erro: {e}")
        
        # TABELA DE GESTÃO - CORREÇÃO DO ERRO NAN
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).execute()
        if res.data:
            f_df = pd.DataFrame(res.data)
            v_list = []
            for i, row in f_df.head(20).iterrows():
                p_pg = len(f_df[f_df['contrato_id'] == row['contrato_id']])
                # Proteção contra NaN no loop
                raw_tp = row['parcelas_total']
                t_parc = int(float(raw_tp)) if raw_tp and str(raw_tp).lower() != 'nan' else 0
                
                v_list.append({
                    "Nome": row['nome_funcionario'],
                    "Banco": row['banco_nome'],
                    "Contrato": row['contrato_id'],
                    "Pagas": p_pg,
                    "Faltam": max(0, t_parc - p_pg),
                    "Dif": f"R$ {row['diferenca']:.2f}"
                })
            st.table(pd.DataFrame(v_list))

# --- 3. ADMIN ---
elif m == "⚙️ Admin":
    st.subheader("⚙️ Painel de Controle")
    pw = st.text_input("Master", type='password')
    if pw == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            c1, c2 = st.columns(2)
            rs = c1.text_input("Razão Social")
            cj = c2.text_input("CNPJ")
            rp = c1.text_input("Representante")
            tl = c2.text_input("Telefone")
            en = st.text_input("Endereço")
            
            # SELEÇÃO DE PLANOS
            plano = st.selectbox("Plano Mensal", ["Prata (Até 50 nomes)", 
                                                "Ouro (Até 200 nomes)", 
                                                "Black (Ilimitado)"])
            
            c3, c4 = st.columns(2)
            us = c3.text_input("Login")
            sn = c3.text_input("Senha", type='password')
            lk = c4.text_input("Link CSV")
            
            if st.form_submit_button("CADASTRAR EMPRESA"):
                v = (datetime.now()+timedelta(30)).isoformat()
                di = {"nome_empresa": rs, "cnpj": cj, "representante": rp,
                "telefone": tl, "endereco": en, "login": us, "senha": h(sn),
                "data_expiracao": v, "link_planilha": lk, "plano": plano}
                sb.table("empresas").insert(di).execute()
                st.success(f"Registrado! Plano: {plano}")
