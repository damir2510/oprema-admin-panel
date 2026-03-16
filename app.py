import streamlit as st
import pandas as pd
import pymysql

st.set_page_config(page_title="Čišćenje Podataka", layout="wide")

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

st.title("🚜 Provera i Čišćenje Tabele")

try:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # 1. Prikaži nam SVE što je baza vratila (da vidimo to "smeće")
        st.write("### 🚩 Sirovi podaci iz baze (pre čišćenja):")
        st.dataframe(df.head(10)) 

        # 2. ČIŠĆENJE: Izbacujemo redove gde je sadržaj isti kao naziv kolone
        # Prolazimo kroz svaku kolonu i brišemo redove koji su identični nazivu te kolone
        for col in df.columns:
            df = df[df[col].astype(str).str.lower().str.strip() != col.lower()]

        # 3. DODATNO: Izbacujemo redove gde su ključna polja prazna ili samo zarezi
        if 'inventarni_broj' in df.columns:
            df = df[df['inventarni_broj'].notna()]
            df = df[df['inventarni_broj'] != ""]

        st.write("---")
        st.write(f"### ✅ Podaci nakon čišćenja (Preostalo: {len(df)} redova):")
        
        if len(df) > 0:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.error("⚠️ Filter je obrisao SVE redove. To znači da su u bazi SVAKI red i SVAKA kolona identični nazivima kolona.")
            st.info("Rešenje: Moraš obrisati tabelu (Truncate) i ponoviti Import, ali u DBeaveru štikliraj 'Header' opciju.")

    else:
        st.warning("Tabela u bazi je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
