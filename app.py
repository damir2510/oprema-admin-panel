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

st.title("🚜 Glavna Evidencija Opreme")

try:
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # Sređivanje naziva kolona radi lakšeg rada (male i bez razmaka)
        df.columns = [c.strip().lower() for c in df.columns]

        # --- PRECIZNIJE ČIŠĆENJE ---
        # Izbacujemo samo redove gde je 'inventarni_broj' baš tekst 'inventarni_broj' 
        # i gde je 'id' (koji je obično broj) zapravo tekst 'id'
        df = df[df['inventarni_broj'].astype(str).str.strip().lower() != 'inventarni_broj']
        df = df[df['id'].astype(str).str.strip().lower() != 'id']
        
        # Izbaci potpuno prazne redove
        df = df.dropna(how='all')

        # --- ODABIR KOLONA ZA PRIKAZ (da ne bude preširoko) ---
        # Možeš dodati ili izbaciti kolone iz ove liste ispod
        vazne_kolone = [
            'inventarni_broj', 'bar_kod', 'vrsta_opreme', 
            'naziv_proizvodjac', 'seriski_broj', 'status', 
            'trenutni_radnik', 'vazi_do'
        ]
        
        # Proveravamo koje od ovih kolona stvarno postoje u bazi
        postojace = [c for c in vazne_kolone if c in df.columns]

        # --- PRETRAGA ---
        search = st.text_input("🔍 Pretraži (po nazivu, radniku, statusu...):", "")
        if search:
            mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # --- FINALNI PRIKAZ ---
        # Prikazujemo samo važne kolone, ali pretraga radi kroz SVE
        st.dataframe(
            df_display[postojace], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.success(f"Pronađeno realnih aparata: {len(df_display)}")
        
        # Opciono: Dugme da vidiš sve kolone ako ti zatrebaju
        if st.checkbox("Prikaži sve tehničke detalje (sve kolone)"):
            st.write(df_display)

    else:
        st.warning("Tabela je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
