import streamlit as st
import pandas as pd
from supabase import create_client
import hashlib
from datetime import datetime, date, timedelta

# ============================================================
# 0) CONFIGURAÇÃO E CSS AVANÇADO
# ============================================================
st.set_page_config(page_title="RRB Auditoria Platinum", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    .stMetric {
        background: rgba(74, 144, 226, 0.0
