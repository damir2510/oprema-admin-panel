import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# Postavke stranice na samom vrhu
st.set_page_config(page_title="Oprema Admin", layout="wide")

# Funkcija za konekciju (Aiven MySQL)
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
st.write("---")

try:
    conn = get_conn()
    # Vučemo sve podatke
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # 1. Sređivanje naziva kolona (uklanjamo razmake i prebacujemo u mala slova)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # 2. Pretraga (radi kroz sve kolone odjednom)
        search = st.text_input("🔍 Pretraži (po nazivu, bar-kodu, radniku...):", "")
        
        if search:
            mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)
            df_prikaz = df[mask]
        else:
            df_prikaz = df

        # 3. Prikaz tabele
        # Streamlit automatski pravi interaktivnu tabelu (sortiranje, širenje)
        st.dataframe(
            df_prikaz, 
            use_container_width=True, 
            hide_index=True
        )

        st.success(f"Prikazano stavki: {len(df_prikaz)}")
        
    else:
        st.warning("Baza je povezana, ali tabela 'oprema' nema podataka.")

except Exception as e:
    st.error(f"Došlo je do greške: {e}")
    st.info("Proveri da li su podaci za konekciju ispravni i da li je Aiven baza aktivna.")

# Footer
st.markdown("---")
st.caption("Verzija 2.0 | Optimizovano za brzi deploy")
