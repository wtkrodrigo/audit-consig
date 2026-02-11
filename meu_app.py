import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG E ESTILO ---
st.set_page_config(page_title="RRB Auditoria", layout="wide")
st.markdown("""<style>
    .stMetric { background: white; padding: 15px; border-radius: 10px; 
    border-left: 5px solid #002D62; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .logo { font-size: 24px; font-weight: bold; color: #002D62; }
</style>""", unsafe_allow_html=True)

def logo():
    st.markdown("<div class='logo'>🛡️ RRB SOLUÇÕES</div>", unsafe_allow_html=True)
    st.write("---")

# --- CONEXÃO ---
try:
    su, sk = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    sb = create_client(su, sk)
except:
    st.error("Erro Secrets/Credenciais"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- NAV ---
st.sidebar.title("MENU")
m = st.sidebar.radio("Ir para:", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# --- 1. FUNCIONÁRIO ---
if m == "👤 Func":
    logo()
    cpf = st.text_input("CPF (somente números)")
    c = "".join(filter(str.isdigit, cpf))
    if st.button("BUSCAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            d = r.data[-1]
            ct = d.get('contrato_id')
            hist = [x for x in r.data if x.get('contrato_id') == ct]
            pg = len(hist)
            v_tp = d.get('parcelas_total')
            tt = int(float(v_tp)) if v_tp and str(v_tp)!='nan' else 0
            st.success(f"Olá, {d['nome_funcionario']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas", f"{pg}/{tt}")
            c2.metric("Valor Mensal", f"R$ {d.get('valor_rh', 0):.2f}")
            c3.metric("Status", "✅ OK" if d['diferenca']==0 else "❌ Alerta")
            if tt > 0: st.progress(min(1.0, pg/tt))

# --- 2. EMPRESA ---
elif m == "🏢 Empresa":
    logo()
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_i, p_i = st.text_input("User"), st.text_input("Pass", type='password')
        if st.button("LOGIN"):
            q = sb.table("empresas").select("*").eq("login", u_i).execute()
            if q.data and h(p_i) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha'); st.rerun()
    else:
        c_t, c_s = st.columns([4, 1])
        c_t.subheader(f"Gestão: {st.session_state.n}")
        if c_s.button("SAIR"): st.session_state.at = False; st.rerun()
        with st.expander("📥 Sincronizar"):
            if st.button("EXECUTAR"):
                try:
                    df = pd.read_csv(st.session_state.lk)
                    df.columns = df.columns.str.strip().str.lower()
                    for _, r in df.iterrows():
                        vr = float(pd.to_numeric(r['valor_rh'], 'coerce') or 0)
                        vb = float(pd.to_numeric(r['valor_banco'], 'coerce') or 0)
                        tp = int(pd.to_numeric(r['total_parcelas'], 'coerce') or 0)
                        p = {"nome_empresa":st.session_state.n,"cpf":str(r['cpf']),
                        "nome_funcionario":str(r['nome']),"valor_rh":vr,"valor_banco":vb,
                        "diferenca":vr-vb,"banco_nome":str(r.get('banco','N/A')),
                        "contrato_id":str(r.get('contrato','N/A')),"parcelas_total":tp,
                        "data_processamento":datetime.now().isoformat()}
                        sb.table("resultados_auditoria").insert(p).execute()
                    st.success("Sincronizado!")
                except Exception as e: st.error(f"Erro: {e}")
        st.write("---")
        res = sb.table("resultados_auditoria").select("*").eq(
            "nome_empresa", st.session_state.n).order("data_processamento").execute()
        if res.data:
            f_df = pd.DataFrame(res.data)
            v_l = []
            for ct in f_df['contrato_id'].unique():
                cd = f_df[f_df['contrato_id'] == ct]
                rw = cd.iloc[-1]
                v_t = rw['parcelas_total']
                tt = int(float(v_t)) if v_t and str(v_t)!='nan' else 0
                pg = len(cd)
                d1 = pd.to_datetime(cd['data_processamento'].min()).strftime('%d/%m/%y')
                d2 = (pd.to_datetime(rw['data_processamento']) + 
                      timedelta(days=30*(tt-pg))).strftime('%d/%m/%y')
                v_l.append({"Nome": rw['nome_funcionario'], "Início": d1, "Fim": d2,
                "Pagas": pg, "Faltam": max(0, tt-pg), "V. RH": f"R$ {rw['valor_rh']:.2f}"})
            st.table(pd.DataFrame(v_l))

# --- 3. ADMIN ---
elif m == "⚙️ Admin":
    logo()
    if st.text_input("Master", type='password') == st.secrets.get("SENHA_MASTER"):
        with st.form("cad"):
            c1, c2 = st.columns(2)
            rs, cj = c1.text_input("Razão"), c2.text_input("CNPJ")
            rp, tl = c1.text_input("Repres."), c2.text_input("Tel")
            en = st.text_input("Endereço")
            pl = st.selectbox("Plano", ["Prata", "Ouro", "Black"])
            c3, c4 = st.columns(2)
            us, sn = c3.text_input("Login"), c3.text_input("Senha", type='password')
            lk = c4.text_input("Link CSV")
            if st.form_submit_button("SALVAR"):
                v = (datetime.now()+timedelta(30)).isoformat()
                d = {"nome_empresa":rs,"cnpj":cj,"representante":rp,"telefone":tl,
                "endereco":en,"login":us,"senha":h(sn),"data_expiracao":v,
                "link_planilha":lk,"plano":pl}
                sb.table("empresas").insert(d).execute(); st.success("OK!")
