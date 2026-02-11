import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(page_title="RRB", layout="wide")

# --- DB ---
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Erro Secrets"); st.stop()

def h(p): return hashlib.sha256(str.encode(p)).hexdigest()

m = st.sidebar.selectbox("Menu", ["👤 Func", "🏢 Empresa", "⚙️ Admin"])

# 1. FUNCIONARIO (VISUALIZAÇÃO DO PROGRESSO)
if m == "👤 Func":
    st.subheader("🔎 Status do Empréstimo")
    c_in = st.text_input("CPF (apenas números)")
    c = "".join(filter(str.isdigit, c_in))
    if st.button("VERIFICAR") and c:
        r = sb.table("resultados_auditoria").select("*").eq("cpf", c).execute()
        if r.data:
            # Pega o lançamento mais recente
            d = r.data[-1]
            st.success(f"Olá, {d['nome_funcionario']}")
            
            # Cálculo de parcelas baseado no histórico do Banco
            contrato = d.get('contrato_id')
            historico = [x for x in r.data if x.get('contrato_id') == contrato]
            pagas = len(historico)
            total = int(d.get('parcelas_total', 0))
            faltam = max(0, total - pagas)

            st.info(f"🏦 {d.get('banco_nome')} | 📄 Contrato: {contrato}")
            
            # Painel de Progresso
            c1, c2, c3 = st.columns(3)
            c1.metric("Parcelas Pagas", f"{pagas} de {total}")
            c2.metric("Restantes", f"{faltam}")
            c3.metric("Status", "Em dia" if d['diferenca']==0 else "Divergente")
            
            # Barra de progresso visual
            if total > 0:
                progresso = pagas / total
                st.progress(progresso)
                st.caption(f"Você já quitou {progresso:.0%} do seu contrato.")
        else:
            st.warning("Dados não localizados.")

# 2. EMPRESA (PROCESSAMENTO COM TOTAL DE PARCELAS)
elif m == "🏢 Empresa":
    if 'at' not in st.session_state: st.session_state.at = False
    if not st.session_state.at:
        u_in, p_in = st.text_input("Login"), st.text_input("Senha", type='password')
        if st.button("Entrar"):
            q = sb.table("empresas").select("*").eq("login", u_in).execute()
            if q.data and h(p_in) == q.data[0]['senha']:
                st.session_state.at, st.session_state.n = True, q.data[0]['nome_empresa']
                st.session_state.lk = q.data[0].get('link_planilha', "")
                st.rerun()
    else:
        st.subheader(f"Painel: {st.session_state.n}")
        if st.button("🔄 LANÇAR PAGAMENTO DO MÊS"):
            try:
                df = pd.read_csv(st.session_state.lk)
                df.columns = df.columns.str.strip().str.lower()
                for _, r in df.iterrows():
                    v_rh, v_ba = float(r['valor_rh']), float(r['valor_banco'])
                    pld = {
                        "nome_empresa": st.session_state.n,
                        "cpf": str(r['cpf']),
                        "nome_funcionario": r['nome'],
                        "valor_rh": v_rh,
                        "valor_banco": v_ba,
                        "diferenca": v_rh - v_ba,
                        "banco_nome": str(r['banco']),
                        "contrato_id": str(r['contrato']),
                        "parcelas_total": int(r['total_parcelas']),
                        "data_processamento": datetime.now().isoformat()
                    }
                    sb.table("resultados_auditoria").insert(pld).execute()
                st.success("✅ Lançamento Mensal Concluído!")
            except Exception as e: st.error(f"Erro: {e}")

# 3. ADMIN (MANTIDO)
elif m == "⚙️ Admin":
    # ... (mesmo código anterior)
