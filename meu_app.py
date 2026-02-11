import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="RRB-SOLUÇÕES | Transparência", layout="wide", page_icon="🛡️")

# --- DESIGN MODERNO (CSS) ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .trust-badge {
        padding: 10px 20px;
        background: linear-gradient(135deg, #002D62 0%, #0056b3 100%);
        color: white;
        border-radius: 50px;
        display: inline-block;
        font-weight: bold;
        font-size: 0.8em;
        margin-bottom: 20px;
    }
    .card-resumo {
        background: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        margin-top: 20px;
    }
    .status-ok { color: #2ecc71; font-weight: 800; }
    .status-err { color: #e74c3c; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Erro nos Secrets.")
    st.stop()

# --- NAVEGAÇÃO ---
menu = ["Portal do Funcionário", "Portal da Empresa", "Administração RRB"]
escolha = st.sidebar.selectbox("Ir para:", menu)

# ---------------------------------------------------------
# 1. PORTAL DO FUNCIONÁRIO (MODERNO)
# ---------------------------------------------------------
if escolha == "Portal do Funcionário":
    st.markdown('<div class="trust-badge">🛡️ SISTEMA DE AUDITORIA INDEPENDENTE</div>', unsafe_allow_html=True)
    st.title("Portal de Transparência do Colaborador")
    st.write("Verifique a precisão dos seus descontos de forma segura e anônima.")

    with st.container():
        c1, c2 = st.columns([2, 1])
        with c1:
            cpf_input = st.text_input("Seu CPF", placeholder="000.000.000-00", help="Digite apenas os números do seu CPF.")
            # Limpeza automática de CPF (remove pontos e traços)
            cpf_busca = "".join(filter(str.isdigit, cpf_input))
            
        with c2:
            st.write("##")
            btn_buscar = st.button("Consultar Transparência")

    if btn_buscar:
        if not cpf_busca:
            st.warning("Por favor, informe seu CPF.")
        else:
            res = supabase.table("resultados_auditoria").select("*").eq("cpf", cpf_busca).order("data_processamento", desc=True).limit(1).execute()
            
            if res.data:
                d = res.data[0]
                st.markdown(f"### Olá, **{d['nome_funcionario']}**")
                st.caption(f"Dados referentes à última auditoria da empresa: **{d['nome_empresa']}**")
                
                st.markdown('<div class="card-resumo">', unsafe_allow_html=True)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Declarado em Folha", f"R$ {d['valor_rh']}")
                m2.metric("Cobrado pelo Banco", f"R$ {d['valor_banco']}")
                
                diff = d['diferenca']
                label_diff = "Diferença Detectada" if diff != 0 else "Diferença"
                m3.metric(label_diff, f"R$ {diff}", delta=-diff if diff != 0 else None, delta_color="normal")
                
                st.write("---")
                
                if d['status'] == "✅ OK":
                    st.markdown("#### STATUS DA AUDITORIA: <span class='status-ok'>CONFORMIDADE TOTAL ✅</span>", unsafe_allow_html=True)
                    st.success("A auditoria independente confirmou que o valor descontado pela empresa é exatamente o que o banco exigiu. Não há irregularidades.")
                else:
                    st.markdown("#### STATUS DA AUDITORIA: <span class='status-err'>DIVERGÊNCIA IDENTIFICADA ⚠️</span>", unsafe_allow_html=True)
                    st.error(f"Foi encontrada uma diferença de **
