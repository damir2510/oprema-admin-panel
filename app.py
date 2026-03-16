import streamlit as st
import pandas as pd
import pymysql

# 1. Postavka stranice
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

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
    # Čitamo tabelu bez ikakvih filtera u SQL-u
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # Standardizujemo nazive kolona da budu mali bez razmaka
        df.columns = [c.strip().lower() for c in df.columns]

        # IZBACUJEMO SAMO REDOVE KOJI SU NASLOVI (ako ih ima u bazi)
        if 'inventarni_broj' in df.columns:
            df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # 2. Pretraga
        search = st.text_input("🔍 Pretraži bilo šta (naziv, radnik, status...):", "")
        if search:
            mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # 3. PRIKAZ (Sakrivanje ID-a i zaključavanje ključnih polja)
        st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,  # SAKRIVA ID POTPUNO
                "inventarni_broj": st.column_config.TextColumn("Inventarni Broj", disabled=True),
                "bar_kod": st.column_config.TextColumn("Bar Kod", disabled=True),
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "status": st.column_config.SelectboxColumn("Status", options=["Ispravno", "Rashod", "Servis", "Rezerva"])
            }
        )
        
        st.success(f"Pronađeno aparata: {len(df_display)}")

    else:
        st.info("Baza je povezana, ali nema podataka u tabeli 'oprema'.")

except Exception as e:
    st.error(f"Greška pri povezivanju: {e}")
