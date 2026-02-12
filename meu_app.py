import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta, date

# ============================================================
# 0) CONFIG STREAMLIT
# ============================================================
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: rgba(28, 131, 225, 0.05);
        padding: 15px 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-text { font-size: 28px; font-weight: bold; color: #002D62; }
    @media (prefers-color-scheme: dark) { .logo-text { color: #4A90E2; } }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 1) FUNÇÕES UTILITÁRIAS
# ============================================================
def render_header(titulo: str):
    st.markdown(f"""
    <div class='logo-container'>
        <span style='font-size: 40px;'>🛡️</span>
        <div class='logo-text'>RRB SOLUÇÕES
            <span style='font-weight:normal; color:var(--text-color); opacity: 0.6; font-size:18px;'>| {titulo}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("---")


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

    # tenta parsear formatos comuns
    # - 'YYYY-MM-DD'
    # - 'YYYY-MM-DDTHH:MM:SS'
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "")).date().strftime("%Y-%m-%d")
        return datetime.fromisoformat(s).date().strftime("%Y-%m-%d")
    except Exception:
        # fallback: mantém só a parte da data se vier com hora separada por espaço
        if " " in s:
            return s.split(" ")[0]
        return s


def require_secrets(*keys: str):
    missing = [k for k in keys if k not in st.secrets or not str(st.secrets.get(k, "")).strip()]
    if missing:
        st.error(f"❌ Secrets ausentes/invalidos: {', '.join(missing)}")
        st.stop()


def init_session():
    defaults = {
        "authenticated": False,
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


# ============================================================
# 2) SUPABASE (conexão + cache de consultas)
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
    # Aqui usa data_processamento como string ISO, mas funciona bem se sempre for ISO.
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
# 3) APP
# ============================================================
init_session()

menu = st.sidebar.radio("Selecione o Portal", ["👤 Funcionário", "🏢 Empresa", "⚙️ Admin Master"])

if menu == "🏢 Empresa" and st.session_state.get("authenticated"):
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Sair da Sessão"):
        logout()


# ============================================================
# 3.1) PORTAL FUNCIONÁRIO
# ============================================================
if menu == "👤 Funcionário":
    render_header("Portal do Funcionário")

    st.info("🔐 Informe seus dados para liberar a consulta.")
    c1, c2 = st.columns(2)
    cpf_in = c1.text_input("CPF (somente números)")
    dt_nasc_in = c2.date_input("Data de Nascimento", min_value=datetime(1930, 1, 1), format="DD/MM/YYYY")
    tel_fim_in = st.text_input("Últimos 4 dígitos do seu telefone", max_chars=4)

    cpf_clean = digits_only(cpf_in)
    tel_fim_clean = digits_only(tel_fim_in)

    can_submit = (len(cpf_clean) == 11) and (len(tel_fim_clean) == 4)

    if st.button("🔓 ACESSAR AUDITORIA", disabled=not can_submit):
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
# 3.2) PAINEL EMPRESA
# ============================================================
elif menu == "🏢 Empresa":
    render_header("Painel da Empresa")

    if not st.session_state["authenticated"]:
        if not st.session_state["reset_mode"]:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")

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

            if st.button("Esqueci minha senha"):
                st.session_state["reset_mode"] = True
                st.rerun()

        else:
            st.subheader("🔑 Recuperar Senha")
            user_reset = st.text_input("Confirme Usuário")
            cnpj_reset = st.text_input("Confirme CNPJ")
            nova_senha = st.text_input("Nova Senha", type="password")
            nova_senha2 = st.text_input("Confirmar Nova Senha", type="password")

            if st.button("ATUALIZAR"):
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

    else:
        empresa = st.session_state["empresa_nome"]
        csv_url = st.session_state["empresa_csv_url"]

        st.subheader(f"Gestão: {empresa}")

        try:
            res_db = fetch_resultados_empresa(empresa)
            df_empresa = pd.DataFrame(res_db) if res_db else pd.DataFrame()
        except Exception as e:
            st.error("Erro ao carregar dados da empresa.")
            st.exception(e)
            df_empresa = pd.DataFrame()

        if not df_empresa.empty and "diferenca" in df_empresa.columns:
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("Total Base", len(df_empresa))
            conformes = len(df_empresa[df_empresa["diferenca"] == 0])
            divergentes = len(df_empresa[df_empresa["diferenca"] != 0])
            c_m2.metric("Conformes", conformes)
            c_m3.metric("Divergentes", divergentes, delta=f"{divergentes} erros" if divergentes > 0 else None, delta_color="inverse")

        st.divider()

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

                        # IMPORTANTÍSSIMO: garanta constraint única compatível com on_conflict
                        # Se quiser manter como estava, volte para "cpf, contrato_id"
                        if payloads:
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

        busca = st.text_input("🔍 Pesquisar Nome ou CPF")
        filtro = st.radio("Filtro de Status:", ["Todos", "✅ Conformes", "⚠️ Divergentes"], horizontal=True)

        if not df_empresa.empty:
            df_f = df_empresa.copy()

            if "diferenca" in df_f.columns:
                if filtro == "✅ Conformes":
                    df_f = df_f[df_f["diferenca"] == 0]
                elif filtro == "⚠️ Divergentes":
                    df_f = df_f[df_f["diferenca"] != 0]

            if busca:
                b = str(busca).strip()
                # Protege caso colunas estejam nulas/ausentes
                if "nome_funcionario" in df_f.columns:
                    mask_nome = df_f["nome_funcionario"].astype(str).str.contains(b, case=False, na=False)
                else:
                    mask_nome = False

                if "cpf" in df_f.columns:
                    mask_cpf = df_f["cpf"].astype(str).str.contains(digits_only(b) or b, na=False)
                else:
                    mask_cpf = False

                df_f = df_f[mask_nome | mask_cpf]

            # ordena divergentes primeiro (se existir coluna)
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


# ============================================================
# 3.3) ADMIN MASTER
# ============================================================
elif menu == "⚙️ Admin Master":
    render_header("Configurações Master")

    require_secrets("SENHA_MASTER")  # sem fallback
    chave = st.sidebar.text_input("Chave Master", type="password")

    if chave != st.secrets["SENHA_MASTER"]:
        st.warning("Informe a Chave Master para acessar.")
        st.stop()

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
