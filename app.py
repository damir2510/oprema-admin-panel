import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# 1. Konfiguracija stranice (Mora biti prva komanda)
st.set_page_config(page_title="Oprema Admin", layout="wide")

# 2. Funkcija za konekciju
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin",
        password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698,
        database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'}
    )

st.title("🚜 Glavna Evidencija Opreme")

try:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # Sređivanje naziva kolona
        df.columns = [c.strip().lower() for c in df.columns]

        # --- ČIŠĆENJE SMEĆA (Izbacujemo naslove koji su ušli u bazu kao redovi) ---
        if 'inventarni_broj' in df.columns:
            # Izbacujemo redove gde je inventarni broj zapravo tekst "inventarni_broj" ili "inventarni broj"
            df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']
            df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni broj']
        
        # Izbaci potpuno prazne redove
        df = df.dropna(how='all')

        # --- PRETRAGA ---
        search = st.text_input("🔍 Pretraži (po nazivu, bar-kodu, radniku...):", "")
        if search:
            mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # --- PRIKAZ ---
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        st.success(f"Pronađeno realnih aparata: {len(df_display)}")

    else:
        st.warning("Tabela je prazna.")

except Exception as e:
    # Ovde se javljala greška jer 'st' nije bio definisan gore
    st.error(f"Greška: {e}")
