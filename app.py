import streamlit as st
import pandas as pd
import pymysql

# 1. ISTA KONEKCIJA KAO U ADMINU
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

# 2. FUNKCIJA KOJA GARANTUJE PRIKAZ (Preuzeta logika iz tvog Admina)
def get_working_data():
    conn = get_conn()
    with conn.cursor() as cur:
        # Vučemo sve podatke iz tabele oprema
        cur.execute("SELECT * FROM oprema")
        rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# KONFIGURACIJA STRANICE
st.set_page_config(page_title="Pregled Opreme", layout="wide")
st.title("🔍 Radni Panel - Evidencija Opreme")

try:
    df = get_working_data()

    if not df.empty:
        # Standardizacija kolona (da pretraga ne pravi greške)
        df.columns = [c.strip().lower() for c in df.columns]

        # --- PAMETNA PRETRAGA ---
        st.info("Pretražite po inventarnom broju, nazivu, radniku ili bar-kodu.")
        search_query = st.text_input("Unesite pojam za pretragu:", key="search_worker")

        if search_query:
            # Pretraga kroz sve kolone istovremeno (case-insensitive)
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # --- PRIKAZ TABELE (Samo za čitanje - bezbedno za radnike) ---
        # Koristimo data_editor ali sa disabled=True za sve kolone
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,  # Sakrivamo ID (kao u Adminu)
                "oprema_id": None, # Sakrivamo FK ako postoji
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "status": st.column_config.TextColumn("Status")
            }
        )

        st.caption(f"Pronađeno stavki: {len(df_display)}")

    else:
        st.warning("Trenutno nema podataka u bazi. Kontaktirajte administratora.")

except Exception as e:
    st.error(f"Greška pri učitavanju podataka: {e}")

st.sidebar.markdown("### Uputstvo")
st.sidebar.write("Ovaj panel služi isključivo za pregled i pretragu opreme. Za izmene koristite Admin Panel.")
