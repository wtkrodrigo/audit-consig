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
        
        # --- BARRA DE FERRAMENTAS (SINCRONIZAR E EXPORTAR) ---
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        
        with col_btn1:
            btn_sync = st.button("🔄 SINCRONIZAR PLANILHA")
        
        # Busca os dados no Banco
        res_db = sb.table("resultados_auditoria").select("*").eq("nome_empresa", st.session_state.n).execute()
        
        if res_db.data:
            df_res = pd.DataFrame(res_db.data)
            
            # Botão de Exportar (CSV)
            with col_btn2:
                csv = df_res.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 EXPORTAR AUDITORIA",
                    data=csv,
                    file_name=f"auditoria_{st.session_state.n}.csv",
                    mime="text/csv",
                )

            if btn_sync:
                try:
                    with st.spinner("Sincronizando..."):
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

            # --- BUSCA E TABELA ---
            st.write("---")
            busca = st.text_input("🔍 Pesquisar Funcionário (Nome ou CPF)", placeholder="Digite para filtrar...")
            
            if busca:
                # Filtra o DataFrame pelo nome ou pelo CPF
                df_res = df_res[
                    df_res['nome_funcionario'].str.contains(busca, case=False, na=False) | 
                    df_res['cpf'].str.contains(busca, na=False)
                ]
            
            # Exibe a tabela formatada
            st.write(f"Exibindo {len(df_res)} registros:")
            st.dataframe(
                df_res, 
                use_container_width=True, 
                hide_index=True,
                column_order=("nome_funcionario", "cpf", "valor_rh", "valor_banco", "diferenca", "banco_nome", "contrato_id", "parcelas_pagas", "parcelas_total")
            )
        else:
            st.info("Nenhum dado encontrado. Clique em Sincronizar para carregar a planilha.")
            if btn_sync: st.rerun()

        if st.sidebar.button("🚪 Sair do Painel"):
            st.session_state.at = False
            st.rerun()
