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
# --- ISPOD PRIKAZA GLAVNE TABELE DODAJ OVO ---

st.write("---")
st.subheader("📄 Matični Karton Instrumenta")

# 1. Unos inventarskog broja u sidebar-u ili direktno
izabrani_broj = st.sidebar.text_input("🔍 Unesi Inventarski Broj za Matični Karton:", "")

if izabrani_broj:
    # Pronalazimo taj jedan red u našem DataFrame-u
    # Koristimo .astype(str) da budemo sigurni da poređenje radi
    karton_data = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]

    if not karton_data.empty:
        instrument = karton_data.iloc[0] # Uzimamo prvi (i jedini) pronađeni red
        
        st.markdown(f"### Inventarski broj: **{izabrani_broj}**")
        
        # Definišemo polja koja želimo u kartonu i njihove lepše nazive
        polja = {
            "Vrsta opreme": "vrsta_opreme",
            "Proizvođač": "proizvodjac",
            "Naziv": "naziv_proizvodjac",
            "Serijski broj": "seriski_broj",
            "Datum baždarenja": "datum_bazdarenja",
            "Važi do": "vazi_do",
            "Radna temperatura": "radna_temperatura",
            "Relativna vlažnost": "rel_vlaznost",
            "Opseg merenja": "opseg_merenja",
            "Klasa tačnosti": "klasa_tacnosti",
            "Preciznost": "preciznost",
            "Podeok": "podeok"
        }

        # Filtriramo samo ona polja koja NISU prazna u bazi
        # Proveravamo da li je vrednost None, prazan string ili "nan"
        popunjena_polja = []
        for label, col in polja.items():
            if col in instrument:
                val = instrument[col]
                if pd.notna(val) and str(val).strip() not in ["", "-", "nan", "None"]:
                    popunjena_polja.append((label, val))

        # 2. PRIKAZ U TRI REDA (Grid sistem)
        if popunjena_polja:
            # Delimo listu polja na grupe od po 4 (da dobijemo otprilike 3 reda ako ima 12 polja)
            broj_kolona = 4
            for i in range(0, len(popunjena_polja), broj_kolona):
                cols = st.columns(broj_kolona)
                for j in range(broj_kolona):
                    if i + j < len(popunjena_polja):
                        label, value = popunjena_polja[i + j]
                        with cols[j]:
                            st.metric(label=label, value=str(value))
        else:
            st.info("Nema dodatnih tehničkih podataka za ovaj instrument.")
            
    else:
        st.warning(f"Instrument sa brojem {izabrani_broj} nije pronađen u bazi.")
else:
    st.info("Ukucajte inventarski broj u polje sa leve strane da vidite detaljan Matični Karton.")


st.sidebar.markdown("### Uputstvo")
st.sidebar.write("Ovaj panel služi isključivo za pregled i pretragu opreme. Za izmene koristite Admin Panel.")
