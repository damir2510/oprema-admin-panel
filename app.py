import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# 1. Konekcija sa bazom
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

# 2. Dobavljanje glavne tabele
def get_working_data():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM oprema")
        rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# Funkcija za bojenje isteklih datuma u tabelama
def highlight_expiry(val):
    if pd.isna(val) or str(val) == '-': return ""
    try:
        if pd.to_datetime(val).date() < datetime.now().date():
            return "background-color: #ff4b4b; color: white"
    except: pass
    return ""

# KONFIGURACIJA STRANICE
st.set_page_config(page_title="Pregled Opreme", layout="wide")
st.title("🔍 Radni Panel - Evidencija Opreme")

try:
    df = get_working_data()

    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

        # --- GLAVNA PRETRAGA ---
        search_query = st.text_input("🔍 Brza pretraga kroz celu tabelu:", key="main_search")
        if search_query:
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.dataframe(df_display, use_container_width=True, hide_index=True, 
                     column_config={"id": None, "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY")})

        # --- MATIČNI KARTON ---
        st.write("---")
        izabrani_broj = st.sidebar.text_input("🔢 Unesi Inventarski Broj za Matični Karton:", "")

        if izabrani_broj:
            rezultat = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]

            if not rezultat.empty:
                instrument = rezultat.iloc[0]
                model_instrumenta = str(instrument.get('naziv_proizvodjac', '')).strip()
                inv_broj_str = str(izabrani_broj)

                st.subheader(f"📄 Matični Karton i Istorija za br: {izabrani_broj}")
                
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠️ Servis", "📏 Etaloniranje", "⚖️ Baždarenje"])

                with tab1:
                    polja = {
                        "Vrsta": "vrsta_opreme", "Proizvođač": "proizvodjac", "Model": "naziv_proizvodjac",
                        "Serijski br.": "seriski_broj", "Zadnje baždarenje": "datum_bazdarenja", "Važi do": "vazi_do",
                        "Opseg": "opseg_merenja", "Klasa": "klasa_tacnosti", "Preciznost": "preciznost", "Podeok": "podeok"
                    }
                    popunjena = [(l, instrument[c]) for l, c in polja.items() if c in instrument and pd.notna(instrument[c]) and str(instrument[c]).strip() not in ["", "-", "nan", "None", "0"]]
                    cols = st.columns(4)
                    for i, (label, val) in enumerate(popunjena):
                        with cols[i % 4]:
                            st.caption(label)
                            st.write(f"**{val}**")

                # --- SAMO OVAJ DEO ZAMENI U TABU 2 ---

                with tab2:
                    st.write(f"Definisani opsezi za model: `{model_instrumenta}`")
                    try:
                        conn = get_conn()
                        # Ovde smo promenili 'naziv_opreme' u 'naziv_proizvodjac' da bi se poklapalo sa tvojom bazom
                        query_k = "SELECT * FROM kulture_opsezi WHERE naziv_proizvodjac = %s"
                        df_k = pd.read_sql(query_k, conn, params=(model_instrumenta,))
                        conn.close()
                        
                        if not df_k.empty:
                            # Čist prikaz bez nepotrebnih tehničkih ID kolona
                            st.dataframe(df_k, use_container_width=True, hide_index=True, 
                                         column_config={"id": None, "id_opreme": None, "naziv_proizvodjac": None})
                        else:
                            st.info(f"Nema definisanih kultura za model {model_instrumenta}.")
                    except Exception as e:
                        st.error(f"Greška u tabeli kulture: {e}")
                        st.info("Proveri da li se kolona u tabeli 'kulture_opsezi' zove 'naziv_proizvodjac' ili samo 'naziv'.")

# --- OSTATAK KODA OSTAJE ISTI ---


                with tab3:
                    conn = get_conn()
                    df_s = pd.read_sql("SELECT datum_servisa, broj_zapisnika, opis_intervencije, izvrsio_servis FROM istorija_servisa WHERE inventarni_broj = %s ORDER BY datum_servisa DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    st.dataframe(df_s, use_container_width=True, hide_index=True) if not df_s.empty else st.write("Nema servisa.")

                with tab4:
                    conn = get_conn()
                    df_e = pd.read_sql("SELECT datum_etaloniranja, broj_sertifikata, vazi_do, laboratorija FROM istorija_etaloniranja WHERE inventarni_broj = %s ORDER BY datum_etaloniranja DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_e.empty:
                        st.dataframe(df_e.style.applymap(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else: st.info("Nema etaloniranja.")

                with tab5:
                    conn = get_conn()
                    df_b = pd.read_sql("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s ORDER BY datum_bazdarenja DESC", conn, params=(inv_broj_str,))
                    conn.close()
                    if not df_b.empty:
                        st.dataframe(df_b.style.applymap(highlight_expiry, subset=['vazi_do']), use_container_width=True, hide_index=True)
                    else: st.info("Nema baždarenja.")

            else:
                st.warning("Instrument nije pronađen.")
        else:
            st.info("Ukucaj inventarski broj u polje levo da otvoriš karton.")

    else:
        st.warning("Tabela oprema je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
