import streamlit as st
import pandas as pd
import pymysql

# 1. Podešavanje stranice
st.set_page_config(page_title="Sistem Oprema - Admin", layout="wide")

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

st.title("📊 Glavna Evidencija Opreme")

try:
    conn = get_conn()
    # Čitamo celu tabelu koju si upravo uvezao
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # Standardizacija naziva kolona
        df.columns = [c.strip().lower() for c in df.columns]

        # Brza pretraga kroz sve podatke (naziv, radnik, status...)
        search = st.text_input("🔍 Pretraži tabelu:", "")
        if search:
            mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)
            df_prikaz = df[mask]
        else:
            df_prikaz = df

        # --- PRIKAZ TABELE (Kao na tvojoj slici, ali bez ID-a) ---
        st.data_editor(
            df_prikaz,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,  # SAKRIVAMO ID (ne treba nam u webu)
                "inventarni_broj": st.column_config.TextColumn("Inv. Broj", disabled=True),
                "bar_kod": st.column_config.TextColumn("Bar Kod", disabled=True),
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "status": st.column_config.SelectboxColumn(
                    "Status", 
                    options=["Ispravno", "Rashod", "Servis", "Rezerva"]
                )
            }
        )
        
        st.success(f"Pronađeno realnih aparata: {len(df_prikaz)}")

    else:
        st.warning("Baza je povezana, ali tabela 'oprema' je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
