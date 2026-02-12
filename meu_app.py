import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta, date

# ============================================================
# 0) CONFIGURAÇÃO
# ============================================================
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")


# ============================================================
# 1) DESIGN CORPORATIVO PREMIUM (CSS)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Background corporativo premium */
.stApp{
  background:
    radial-gradient(1200px 800px at 12% 10%, rgba(74,144,226,0.16), transparent 60%),
    radial-gradient(900px 700px at 90% 18%, rgba(0,45,98,0.18), transparent 55%),
    linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,248,255,1));
}

/* Container principal */
section.main > div { padding-top: 1.1rem; }

/* Métricas: card premium */
[data-testid="stMetric"]{
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(0,45,98,0.10);
  padding: 16px 18px;
  border-radius: 16px;
  box-shadow: 0 12px 26px rgba(0,0,0,0.06);
  backdrop-filter: blur(10px);
}

/* Dataframe container (um pouco mais suave) */
[data-testid="stDataFrame"]{
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(0,45,98,0.08);
}

/* Botões (geral) */
.stButton > button{
  border-radius: 14px;
  border: 1px solid rgba(0,45,98,0.18);
  padding: 0.72rem 1rem;
  font-weight: 800;
  box-shadow: 0 10px 22px rgba(0,0,0,0.06);
  transition: transform .06s ease, box-shadow .2s ease, filter .2s ease;
}
.stButton > button:hover{
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(0,0,0,0.10);
  filter: brightness(1.02);
}

/* Sidebar mais elegante */
[data-testid="stSidebar"] > div {
  background: linear-gradient(180deg, rgba(0,45,98,0.92), rgba(0,45,98,0.78));
}
[data-testid="stSidebar"] * {
  color: white !important;
}
[data-testid="stSidebar"] a {
  color: #CFE6FF !important;
  text-decoration: none;
}

/* Header premium */
.rrb-header{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  margin-bottom:14px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255,255,255,0.62);
  border: 1px solid rgba(0,45,98,0.10);
  box-shadow: 0 14px 34px rgba(0,0,0,0.06);
  backdrop-filter: blur(10px);
}
.rrb-left{ display:flex; align-items:center; gap:14px; }
.rrb-shield{
  width:46px;height:46px;border-radius:14px;
  background: linear-gradient(135deg, rgba(0,45,98,1), rgba(74,144,226,1));
  display:flex;align-items:center;justify-content:center;
  box-shadow: 0 14px 30px rgba(0,45,98,0.22);
  color:white;font-size:22px;
}
.rrb-title{
  font-size: 26px;
  font-weight: 900;
  letter-spacing: 0.2px;
  color: #002D62;
  margin: 0;
  line-height: 1.05;
}
.rrb-subtitle{
  margin-top: 6px;
  color: rgba(20, 30, 45, 0.60);
  font-size: 13px;
  font-weight: 650;
}
.rrb-badge{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  background: rgba(74,144,226,0.14);
  color: #0B3D91;
  border: 1px solid rgba(74,144,226,0.25);
}

/* Botão WhatsApp no topo */
.rrb-wpp{
  display:inline-flex;
  align-items:center;
  gap:10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: linear-gradient(135deg, #25D366, #128C7E);
  color: white !important;
  font-weight: 900;
  border: 1px solid rgba(255,255,255,0.25);
  text-decoration: none !important;
  box-shadow: 0 16px 32px rgba(18,140,126,0.22);
  transition: transform .06s ease, filter .2s ease;
  white-space: nowrap;
}
.rrb-wpp:hover{
  transform: translateY(-1px);
  filter: brightness(1.03);
}
.rrb-wpp small{ opacity: 0.92; font-weight: 800; }

/* Bloco "glass" para seções */
.rrb-glass{
  background: rgba(255,255,255,0.62);
  border: 1px solid rgba(0,45,98,0.10);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: 0 14px 34px rgba(0,0,0,0.05);
  backdrop-filter: blur(10px);
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2) HELPERS / UTILITÁRIOS
# ============================================================
def sha256_hex(p: str) -> str:
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()


def digits_only(s: str) -> str:
    return "".join(filter(str.isdigit, str(s or "")))


def normalize_date_yyyy_mm_dd(value) -> str:
    """
    Retorna 'YYYY-MM-DD' quando possível.
    Aceita date/datetime/str.
    """
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")

    s = str(value).strip()
    if not s:
        return ""

    try:
        # lida com "YYYY-MM-DD" e "YYYY-MM-DDTHH:MM:SS"
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "")).date().strftime("%Y-%m-%d")
        return datetime.fromisoformat(s).date().strftime("%Y-%m-%d")
    except Exception:
        # fallback (se vier "YYYY-MM-DD HH:MM:SS")
        if " " in s:
            return s.split(" ")[0]
        return s


def init_session():
    defaults = {
        "authenticated": False,    # empresa logada?
        "empresa_nome": None,
        "empresa_csv_url": None,
        "reset_mode": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def require_secrets(*keys: str):
    missing = [k for k in keys if k not in st.secrets or not str(st.secrets.get(k, "")).strip()]
    if missing:
        st.error(f"❌ Secrets ausentes/invalidos: {', '.join(missing)}")
        st.stop()


def build_whatsapp_url(menu_atual: str) -> str:
    numero = "5513996261907"
    empresa = st.session_state.get("empresa_nome") or ""
    base = "Olá! Preciso de suporte no portal de auditoria da RRB Soluções."
    if empresa:
        base += f"\nEmpresa: {empresa}"
    base += f"\nPortal: {menu_atual}"
    msg = base.replace(" ", "%20").replace("\n", "%0A")
    return f"https://wa.me/{numero}?text={msg}"


def render_header(titulo: str, menu_atual: str):
    wpp_url = build_whatsapp_url(menu_atual)
    st.markdown(f"""
    <div class="rrb-header">
      <div class="rrb-left">
        <div class="rrb-shield">🛡️</div>
        <div>
          <div class="rrb-title">RRB Soluções</div>
          <div class="rrb-subtitle"><span class="rrb-badge">{titulo}</span></div>
        </div>
      </div>

      <a class="rrb-wpp" href="{wpp_url}" target="_blank" rel="noopener">
        <span style="font-size:18px;">💬</span>
        <div style="line-height:1.05;">
          Falar com Suporte<br><small>WhatsApp • Resposta rápida</small>
        </div>
      </a>
    </div>

    <hr style="border:none; height:1px; background:rgba(0,45,98,0.10); margin: 10px 0 18px 0;" />
    """, unsafe_allow_html=True)


def render_faq_empresa():
    st.markdown("## ❓ FAQ da Empresa")
    st.caption("Dúvidas comuns e sugestões de soluções para manter a auditoria sempre consistente.")

    with st.expander("1) O que significa 'Divergência' e o que devo checar primeiro?"):
        st.write("""
**Divergência** ocorre quando o **Valor RH** é diferente do **Valor Banco/Contrato**.

Checklist rápido:
- confirme se **contrato_id** no CSV é o mesmo do banco/contrato real
- verifique **renegociação/amortização/portabilidade** (mudam valor e prazo)
- revise se o RH está usando **a planilha mais recente**
- confira se há diferença por **arredondamento** (centavos) e padronize o cálculo
        """)

    with st.expander("2) A sincronização do CSV falha. O que costuma causar isso?"):
        st.write("""
Causas frequentes:
- link não é CSV “direto” (ex.: link de visualização do Google Drive/Sheets)
- cabeçalho/nomes de colunas diferentes do esperado
- campos numéricos em formato inconsistente (vírgula/ponto)
- colunas com espaços extras

Solução recomendada:
- garanta um link que baixe CSV diretamente
- padronize colunas e revise o cabeçalho
- teste o link abrindo em aba anônima (se pedir login, não é “direto”)
        """)

    with st.expander("3) Quais colunas são recomendadas no CSV?"):
        st.write("Sugestão de padrão (ajuste conforme sua operação):")
        st.code(
            "cpf, nome, data_nascimento, telefone, banco, contrato, "
            "valor_rh, valor_banco, valor_emprestimo, total_parcelas, parcelas_pagas",
            language="text"
        )

    with st.expander("4) Como reduzir divergências recorrentes (boas práticas)?"):
        st.write("""
Recomendações:
- registre **data_processamento** e faça auditoria por período (mensal)
- valide CPF (11 dígitos) e contrato_id (não vazio) antes do upsert
- mantenha histórico de alterações do contrato (se possível)
- padronize o cálculo de diferença (ex.: sempre 2 casas decimais)
        """)

    with st.expander("5) Sugestões de melhorias (próximos passos)"):
        st.write("""
Sugestões de evolução:
- criar um painel de “Top divergências” por banco/filial
- armazenar “motivo”/status de tratamento (em análise, resolvido, pendente)
- habilitar RLS no Supabase para isolar dados por empresa (segurança)
- trocar hash de senha para **bcrypt/argon2** (segurança)
        """)


# ============================================================
# 3) SUPABASE (conexão + cache de consultas)
# ============================================================
require_secrets("SUPABASE_URL", "SUPABASE_KEY")
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"❌ Falha crítica na conexão com Supabase: {e}")
    st.stop()


@st.cache_data(ttl=60)
def fetch_empresa_por_login(login: str):
    return sb.table("empresas").select("*").eq("login", login).execute().data


@st.cache_data(ttl=60)
def fetch_resultados_empresa(nome_empresa: str):
    return sb.table("resultados_auditoria").select("*").eq("nome_empresa", nome_empresa).execute().data


@st.cache_data(ttl=60)
def fetch_ultimo_resultado_por_cpf(cpf: str):
    # Ajuste o campo de ordenação conforme seu schema (created_at / data_processamento / id)
    return (
        sb.table("resultados_auditoria")
        .select("*")
        .eq("cpf", cpf)
        .order("data_processamento", desc=True)
        .limit(1)
        .execute()
        .data
    )


def clear_caches():
    st.cache_data.clear()


# ============================================================
# 4) APP
# ============================================================
init_session()

menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])
st.sidebar.write("")
st.sidebar.caption("RRB Soluções • Auditoria e Conformidade")


# ============================================================
# 4.1) PORTAL FUNCIONÁRIO
# ============================================================
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário", menu)

    st.markdown('<div class="rrb-glass">', unsafe_allow_html=True)
    st.info("🔐 Informe seus dados para liberar a consulta.")
    c1, c2 = st.columns(2)
    cpf_in = c1.text_input("CPF (somente números)")
    dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930, 1, 1), format="DD/MM/YYYY")
    tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)
    st.markdown("</div>", unsafe_allow_html=True)

    cpf_clean = digits_only(cpf_in)
    tel_fim_clean = digits_only(tel_fim_in)
    can_submit = (len(cpf_clean) == 11) and (len(tel_fim_clean) == 4)

    if st.button("🔓 ACESSAR AUDITORIA", disabled=not can_submit, use_container_width=True):
        try:
            res = fetch_ultimo_resultado_por_cpf(cpf_clean)
            if not res:
                st.warning("CPF não localizado.")
                st.stop()

            d = res[0]
            nasc_db = normalize_date_yyyy_mm_dd(d.get("data_nascimento"))
            nasc_in = normalize_date_yyyy_mm_dd(dt_nasc_in)

            tel_db = digits_only(d.get("telefone", ""))
            ok_nasc = (nasc_db == nasc_in)
            ok_tel = tel_db.endswith(tel_fim_clean)

            if not (ok_nasc and ok_tel):
                st.error("Dados de validação incorretos.")
                st.stop()

            st.success(f"Bem-vindo, {d.get('nome_funcionario', 'Funcionário')}")

            m1, m2, m3 = st.columns(3)
            m1.metric("Mensalidade RH", f"R$ {float(d.get('valor_rh', 0) or 0):,.2f}")
            m2.metric("Banco", d.get("banco_nome", "N/A"))

            diferenca = float(d.get("diferenca", 0) or 0)
            status = "✅ CONFORME" if abs(diferenca) < 0.005 else "⚠️ DIVERGÊNCIA"
            m3.metric("Status", status)

            with st.expander("📊 Detalhes do Contrato"):
                st.write(
                    f"**Empréstimo:** R$ {float(d.get('valor_emprestimo', 0) or 0):,.2f} "
                    f"| **ID:** {d.get('contrato_id', 'N/A')}"
                )
                pp = int(d.get("parcelas_pagas", 0) or 0)
                pt = int(d.get("parcelas_total", 0) or 0)
                st.write(f"**Parcelas:** {pp} de {pt}")
                if pt > 0:
                    st.progress(min(pp / pt, 1.0))

        except Exception as e:
            st.error("Erro ao consultar base de dados.")
            st.exception(e)


# ============================================================
# 4.2) PAINEL EMPRESA
# ============================================================
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa", menu)

    if st.session_state.get("authenticated"):
        st.sidebar.write("---")
        st.sidebar.success(f"Logado: {st.session_state.get('empresa_nome')}")
        if st.sidebar.button("🚪 Sair da Sessão", use_container_width=True):
            logout()

    if not st.session_state["authenticated"]:
        # LOGIN / RESET
        if not st.session_state["reset_mode"]:
            st.markdown('<div class="rrb-glass">', unsafe_allow_html=True)
            st.subheader("Acesso Administrativo")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")

            cols = st.columns([1.2, 1])
            with cols[0]:
                if st.button("ACESSAR", use_container_width=True):
                    try:
                        q = fetch_empresa_por_login(u)
                        if q and sha256_hex(p) == q[0].get("senha"):
                            st.session_state["authenticated"] = True
                            st.session_state["empresa_nome"] = q[0].get("nome_empresa")
                            st.session_state["empresa_csv_url"] = q[0].get("link_planilha")
                            st.session_state["reset_mode"] = False
                            st.rerun()
                        else:
                            st.error("Login ou senha inválidos.")
                    except Exception as e:
                        st.error("Erro ao autenticar.")
                        st.exception(e)

            with cols[1]:
                if st.button("Esqueci minha senha", use_container_width=True):
                    st.session_state["reset_mode"] = True
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.markdown('<div class="rrb-glass">', unsafe_allow_html=True)
            st.subheader("🔑 Recuperar Senha")
            st.caption("Confirme usuário e CNPJ para definir uma nova senha.")
            user_reset = st.text_input("Confirme Usuário")
            cnpj_reset = st.text_input("Confirme CNPJ")
            nova_senha = st.text_input("Nova Senha", type="password")
            nova_senha2 = st.text_input("Confirmar Nova Senha", type="password")

            cols = st.columns([1, 1])
            with cols[0]:
                if st.button("ATUALIZAR", use_container_width=True):
                    if len(nova_senha) < 8:
                        st.error("A nova senha precisa ter pelo menos 8 caracteres.")
                        st.stop()
                    if nova_senha != nova_senha2:
                        st.error("As senhas não coincidem.")
                        st.stop()

                    try:
                        check = (
                            sb.table("empresas")
                            .select("*")
                            .eq("login", user_reset)
                            .eq("cnpj", cnpj_reset)
                            .execute()
                        )
                        if check.data:
                            sb.table("empresas").update({"senha": sha256_hex(nova_senha)}).eq("login", user_reset).execute()
                            clear_caches()
                            st.success("Sucesso! Faça login com a nova senha.")
                            st.session_state["reset_mode"] = False
                            st.rerun()
                        else:
                            st.error("Usuário/CNPJ não conferem.")
                    except Exception as e:
                        st.error("Erro ao atualizar senha.")
                        st.exception(e)

            with cols[1]:
                if st.button("Voltar para Login", use_container_width=True):
                    st.session_state["reset_mode"] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # LOGADO
        empresa = st.session_state["empresa_nome"]
        csv_url = st.session_state["empresa_csv_url"]

        st.markdown('<div class="rrb-glass">', unsafe_allow_html=True)
        st.subheader(f"Gestão: {empresa}")
        st.caption("Sincronize o CSV para manter os dados atualizados e filtre divergências rapidamente.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Carrega dados
        try:
            res_db = fetch_resultados_empresa(empresa)
            df_empresa = pd.DataFrame(res_db) if res_db else pd.DataFrame()
        except Exception as e:
            st.error("Erro ao carregar dados da empresa.")
            st.exception(e)
            df_empresa = pd.DataFrame()

        # KPIs
        if not df_empresa.empty and "diferenca" in df_empresa.columns:
            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            c_m1.metric("Total Base", len(df_empresa))
            conformes = len(df_empresa[df_empresa["diferenca"] == 0])
            divergentes = len(df_empresa[df_empresa["diferenca"] != 0])
            c_m2.metric("Conformes", conformes)
            c_m3.metric("Divergentes", divergentes, delta=f"{divergentes} casos" if divergentes else None, delta_color="inverse")

            # Última sincronização (se tiver data_processamento)
            if "data_processamento" in df_empresa.columns and df_empresa["data_processamento"].notna().any():
                try:
                    last = pd.to_datetime(df_empresa["data_processamento"], errors="coerce").max()
                    c_m4.metric("Última atualização", last.strftime("%d/%m/%Y %H:%M") if pd.notna(last) else "—")
                except Exception:
                    c_m4.metric("Última atualização", "—")
            else:
                c_m4.metric("Última atualização", "—")

        st.divider()

        # Ações
        c_act1, c_act2, c_act3 = st.columns([1, 1, 2])

        with c_act1:
            if st.button("🔄 SINCRONIZAR CSV", use_container_width=True):
                if not csv_url:
                    st.error("URL do CSV não configurada para esta empresa.")
                    st.stop()

                try:
                    with st.spinner("Sincronizando..."):
                        df = pd.read_csv(csv_url)
                        df.columns = df.columns.str.strip().str.lower()

                        def safe_num(x):
                            v = pd.to_numeric(x, errors="coerce")
                            return 0.0 if pd.isna(v) else float(v)

                        def safe_int(x):
                            v = pd.to_numeric(x, errors="coerce")
                            return 0 if pd.isna(v) else int(v)

                        payloads = []
                        for _, r in df.iterrows():
                            vr = safe_num(r.get("valor_rh", 0))
                            vb = safe_num(r.get("valor_banco", 0))

                            payloads.append({
                                "nome_empresa": empresa,
                                "cpf": digits_only(r.get("cpf", "")),
                                "nome_funcionario": str(r.get("nome", "N/A")),
                                "valor_rh": vr,
                                "valor_banco": vb,
                                "valor_emprestimo": safe_num(r.get("valor_emprestimo", 0)),
                                "diferenca": round(vr - vb, 2),
                                "banco_nome": str(r.get("banco", "N/A")),
                                "contrato_id": str(r.get("contrato", "N/A")),
                                "parcelas_total": safe_int(r.get("total_parcelas", 0)),
                                "parcelas_pagas": safe_int(r.get("parcelas_pagas", 0)),
                                "data_nascimento": normalize_date_yyyy_mm_dd(r.get("data_nascimento", "")),
                                "telefone": digits_only(r.get("telefone", "")),
                                "data_processamento": datetime.now().isoformat(),
                            })

                        if payloads:
                            # ATENÇÃO: isso exige UNIQUE compatível no Postgres.
                            # Se sua constraint for só (cpf, contrato_id), mude para "cpf,contrato_id"
                            sb.table("resultados_auditoria").upsert(
                                payloads,
                                on_conflict="nome_empresa,cpf,contrato_id"
                            ).execute()

                            clear_caches()
                            st.toast("Sincronização concluída com sucesso!")
                            st.rerun()

                except Exception as e:
                    st.error(f"Erro na sincronização: {e}")
                    st.exception(e)

        with c_act2:
            if not df_empresa.empty:
                st.download_button(
                    "📥 EXPORTAR",
                    df_empresa.to_csv(index=False).encode("utf-8"),
                    file_name="auditoria.csv",
                    use_container_width=True
                )

        # Filtros
        busca = st.text_input("🔍 Pesquisar Nome ou CPF", placeholder="Ex.: Maria ou 12345678901")
        filtro = st.radio("Filtro de Status:", ["Todos", "✅ Conformes", "⚠️ Divergentes"], horizontal=True)

        # Tabela
        if not df_empresa.empty:
            df_f = df_empresa.copy()

            if "diferenca" in df_f.columns:
                if filtro == "✅ Conformes":
                    df_f = df_f[df_f["diferenca"] == 0]
                elif filtro == "⚠️ Divergentes":
                    df_f = df_f[df_f["diferenca"] != 0]

            if busca:
                b = str(busca).strip()
                if "nome_funcionario" in df_f.columns:
                    mask_nome = df_f["nome_funcionario"].astype(str).str.contains(b, case=False, na=False)
                else:
                    mask_nome = False

                if "cpf" in df_f.columns:
                    mask_cpf = df_f["cpf"].astype(str).str.contains(digits_only(b) or b, na=False)
                else:
                    mask_cpf = False

                df_f = df_f[mask_nome | mask_cpf]

            # Ordena divergentes primeiro (pela diferença absoluta)
            if "diferenca" in df_f.columns:
                df_f = df_f.sort_values(by="diferenca", key=lambda s: s.abs(), ascending=False)

            st.dataframe(
                df_f,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "valor_rh": st.column_config.NumberColumn("Valor RH", format="R$ %.2f"),
                    "valor_banco": st.column_config.NumberColumn("Valor Banco", format="R$ %.2f"),
                    "diferenca": st.column_config.NumberColumn("Diferença", format="R$ %.2f"),
                }
            )

        # FAQ (apenas Empresa)
        st.divider()
        render_faq_empresa()


# ============================================================
# 4.3) ADMIN MASTER
# ============================================================
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master", menu)

    require_secrets("SENHA_MASTER")  # sem fallback (seguro)
    chave = st.sidebar.text_input("Chave Master", type="password")

    if chave != st.secrets["SENHA_MASTER"]:
        st.warning("Informe a Chave Master para acessar.")
        st.stop()

    st.markdown('<div class="rrb-glass">', unsafe_allow_html=True)
    with st.form("f_adm"):
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
        se = c8.text_input("Senha", type="password")
        lk = c9.text_input("URL Planilha (CSV)")

        if st.form_submit_button("✅ SALVAR EMPRESA"):
            if not (razao and lo and se):
                st.error("Preencha pelo menos Razão Social, Login e Senha.")
                st.stop()

            dt = {
                "nome_empresa": razao,
                "cnpj": cnpj,
                "representante": rep,
                "telefone": tel,
                "endereco": end,
                "plano": plano,
                "login": lo,
                "senha": sha256_hex(se),
                "link_planilha": lk,
                "data_expiracao": (datetime.now() + timedelta(days=365)).isoformat()
            }

            try:
                sb.table("empresas").insert(dt).execute()
                clear_caches()
                st.success("Empresa cadastrada com sucesso!")
                st.rerun()
            except Exception as e:
                st.error("Erro ao salvar empresa.")
                st.exception(e)
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("---")
    st.subheader("🏢 Empresas Ativas")
    try:
        em = sb.table("empresas").select("*").execute()
        if em.data:
            st.dataframe(
                pd.DataFrame(em.data)[["nome_empresa", "cnpj", "representante", "plano"]],
                use_container_width=True,
                hide_index=True
            )
    except Exception as e:
        st.error("Erro ao carregar lista de empresas.")
        st.exception(e)
