import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, timedelta

# --- 1. DESIGN SYSTEM ADAPTATIVO ---
st.set_page_config(page_title="RRB Soluções Auditoria", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px;
        border-radius: 16px;
        border-top: 5px solid #002D62;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .header-box {
        background: linear-gradient(135deg, #002D62 0%, #001529 100%);
        padding: 25px; border-radius: 15px; color: white;
        margin-bottom: 30px; display: flex; align-items: center; gap: 20px;
    }

    .footer-note {
        font-size: 12px; color: var(--text-color); opacity: 0.6;
        text-align: center; margin-top: 50px; padding: 20px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
    }
</style>
""", unsafe_allow_html=True)

def render_header(titulo):
    st.markdown(f"""
    <div class="header-box">
        <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 12px;">
            <span style="font-size: 35px;">🛡️</span>
        </div>
        <div>
            <div style="font-size: 26px; font-weight: 800; line-height: 1.1; color: white;">RRB SOLUÇÕES</div>
            <div style="font-size: 15px; opacity: 0.8; color: white;">{titulo}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    st.markdown(f"""
    <div class="footer-note">
        <p>© {datetime.now().year} RRB Soluções em Auditoria. Todos os direitos reservados.</p>
        <p><b>Privacidade e Segurança:</b> Este sistema utiliza criptografia de ponta a ponta. 
        Proteção total conforme LGPD.</p>
