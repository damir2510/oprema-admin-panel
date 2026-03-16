import streamlit as st
import pandas as pd
import pymysql

# 1. Osnovna konfiguracija
st.set_page_config(page_title="Test Podataka", layout="wide")

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

st.title("🔍 Provera tabele: Oprema")

try:
    conn = get_conn()
    # Uzimamo SVE bez ikakvih uslova
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        st.success(f"Uspešno povučeno {len(df)} redova iz baze!")
        
        # Prikazujemo prvih 10 redova u najjednostavnijem formatu
        st.write("### Prvih 10 zapisa:")
        st.dataframe(df.head(10), use_container_width=True)
        
        # Ispisujemo nazive kolona da potvrdimo da su tu
        st.write("### Kolone koje su pronađene:")
        st.write(list(df.columns))

    else:
        st.warning("Konekcija je uspela, ali je tabela 'oprema' u bazi potpuno PRAZNA.")

except Exception as e:
    st.error(f"Greška pri povezivanju na bazu: {e}")
