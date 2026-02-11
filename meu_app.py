import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide")

# CSS Ajustado para Dark Mode e Light Mode
st.markdown("""<style>
    /* Estilo adaptativo para os cards de métricas (Mensalidade RH, Banco, Status) */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        padding: 15px 20px;
        border-radius: 12px;
        border-top: 4px solid #002D62;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Ajuste para o texto das métricas não sumir no dark mode */
    [data-testid="stMetric"] label, [data-testid="stMetric"] div {
        color: var(--text-color) !important;
    }

    .logo-container { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    
    /* Título do logo adaptativo */
    .logo-text { 
        font-size: 28px; 
        font-weight: bold; 
        color: #002D62; 
    }
    
    /* Ajuste de cor do logo para melhor contraste no Dark Mode */
    @media (prefers-color-scheme: dark) {
        .logo-text { color: #4A90E2; }
    }

    .admin-card { 
        background-color: var(--secondary-background-color); 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        margin-bottom: 20px; 
    }
