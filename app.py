import streamlit as st
import pandas as pd
import pymysql

# 1. Konekcija
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

# 2. Dobavljanje podataka
def get_working_data():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM oprema")
        rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# KONFIGURACIJA
st.set_page_config(page_title="Pregled Opreme", layout="wide")
st.title("🔍 Radni Panel - Evidencija Opreme")

try:
    df = get_working_data()

    if not df.empty:
        # Čišćenje kolona
        df.columns = [c.strip().lower() for c in df.columns]

        # --- PRETRAGA ---
        st.info("Pretražite po inventarnom broju, nazivu, radniku ili bar-kodu.")
        search_query = st.text_input("Unesite pojam za pretragu:", key="search_worker")

        if search_query:
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # --- PRIKAZ TABELE ---
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "oprema_id": None,
                "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY"),
                "status": st.column_config.TextColumn("Status")
            }
        )
        st.caption(f"Pronađeno stavki: {len(df_display)}")

        # --- MATIČNI KARTON ---
        st.write("---")
        st.subheader("📄 Matični Karton Instrumenta")

        # Sidebar unos
        izabrani_broj = st.sidebar.text_input("🔍 Unesi Inventarski Broj za Matični Karton:", "")

        if izabrani_broj:
            # Tražimo u ORIGINALNOM df-u da ne bi zavisilo od pretrage gore
            rezultat = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]

            if not rezultat.empty:
                instrument = rezultat.iloc[0] # Uzimamo prvi red
                
                st.markdown(f"### Instrument br: <span style='color:#ff4b4b'>{izabrani_broj}</span>", unsafe_allow_html=True)
                
                # Mapa polja: "Lep naziv": "kolona_u_bazi"
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

                popunjena_polja = []
                for label, col in polja.items():
                    if col in instrument:
                        val = instrument[col]
                        # Provera da li ima smisla prikazati polje
                        if pd.notna(val) and str(val).strip() not in ["", "-", "nan", "None", "0"]:
                            popunjena_polja.append((label, val))

                # Prikaz u gridu (4 kolone po redu)
                if popunjena_polja:
                    cols_per_row = 4
                    for i in range(0, len(popunjena_polja), cols_per_row):
                        st_cols = st.columns(cols_per_row)
                        for j in range(cols_per_row):
                            if i + j < len(popunjena_polja):
                                label, value = popunjena_polja[i + j]
                                with st_cols[j]:
                                    st.markdown(f"**{label}**")
                                    st.code(value) # Code format ga čini uočljivijim
                else:
                    st.info("Ovaj instrument nema unetih tehničkih karakteristika.")
            else:
                st.warning(f"Instrument sa brojem {izabrani_broj} nije pronađen.")
        else:
            st.info("Ukucajte inventarski broj u polje sa leve strane.")

    else:
        st.warning("Baza je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")

st.sidebar.markdown("---")
st.sidebar.write("💡 Savet: Karton se generiše automatski na osnovu popunjenih polja u bazi.")
