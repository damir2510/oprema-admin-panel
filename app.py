import streamlit as st
import pandas as pd
import pymysql

# 1. Konfiguracija
st.set_page_config(page_title="Oprema Admin", layout="wide")

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

st.title("🚜 Provera podataka u bazi")

try:
    conn = get_conn()
    df_raw = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df_raw.empty:
        # POKAZUJE NAM ŠTA JE STVARNO U BAZI (Sve kolone)
        st.write("### 1. Nazivi kolona koje baza šalje:")
        st.code(list(df_raw.columns))

        # Sređivanje naziva kolona radi lakšeg rada
        df_raw.columns = [c.strip().lower() for c in df_raw.columns]

        # POKAZUJE NAM PRVIH 5 REDOVA (Da vidimo kako izgledaju podaci)
        st.write("### 2. Prvih 5 redova iz baze (sirovi podaci):")
        st.dataframe(df_raw.head(5))

        # --- TEST ČIŠĆENJA ---
        # Ovde ćemo biti manje strogi - izbacujemo red samo ako je TAČNO "inventarni_broj"
        if 'inventarni_broj' in df_raw.columns:
             # Privremeno isključujemo strogi filter da vidimo sve
             df_cisto = df_raw[df_raw['inventarni_broj'].astype(str).str.lower().str.strip() != 'inventarni_broj']
        else:
             df_cisto = df_raw

        st.write("### 3. Tabela nakon osnovnog čišćenja:")
        st.dataframe(df_cisto, use_container_width=True, hide_index=True)
        st.success(f"Pronađeno redova: {len(df_cisto)}")

    else:
        st.error("Baza je povezana, ali je tabela 'oprema' prazna!")

except Exception as e:
    st.error(f"Greška: {e}")
