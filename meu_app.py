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
            else: st.error("Login inválido.")
    else:
        st.subheader(f"Gestão: {st.session_state.n}")
        
        # --- NOVO: BARRA DE FERRAMENTAS (SINCRONIZAR E EXPORTAR) ---
        col_btn1, col_btn2, _ = st.columns([1, 1, 2])
        
        with col_btn1:
            if st.button("🔄 SINCRONIZAR AGORA"):
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
                    st.success("Sincronizado!")
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

        # Busca dados para busca e exportação
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        df_res = pd.DataFrame(res_db.data) if res_db.data else pd.DataFrame()

        with col_btn2:
            if not df_res.empty:
                csv = df_res.to_csv(index=False).encode('utf-8')
                st.download_button("📥 EXPORTAR CSV", csv, f"auditoria_{st.session_state.n}.csv", "text/csv")

        st.divider()

        # --- NOVO: CAMPO DE PESQUISA ---
        busca = st.text_input("🔍 Pesquisar funcionário por nome ou CPF")
        
        if not df_res.empty:
            if busca:
                # Filtra o dataframe baseado no input de busca
                df_res = df_res[
                    df_res['nome_funcionario'].astype(str).str.contains(busca, case=False) | 
                    df_res['cpf'].astype(str).str.contains(busca)
                ]
            
            st.dataframe(df_res, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado encontrado para esta empresa.")
