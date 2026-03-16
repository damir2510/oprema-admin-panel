import streamlit as st
import pandas as pd
import pymysql

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

# KONFIGURACIJA STRANICE
st.set_page_config(page_title="Pregled Opreme", layout="wide")
st.title("🔍 Radni Panel - Evidencija Opreme")

try:
    df = get_working_data()

    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

        # --- GLAVNA PRETRAGA ---
        search_query = st.text_input("🔍 Pretraži tabelu (ukucaj bilo šta):", key="main_search")
        if search_query:
            mask = df.astype(str).apply(lambda r: r.str.contains(search_query, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        st.dataframe(df_display, use_container_width=True, hide_index=True, 
                     column_config={"id": None, "vazi_do": st.column_config.DateColumn("Važi do", format="DD.MM.YYYY")})

        # --- MATIČNI KARTON ---
        st.write("---")
        st.subheader("📄 Matični Karton i Istorija")

        # PRVO DEFINIŠEMO BROJ (Sidebar)
        izabrani_broj = st.sidebar.text_input("🔢 Unesi Inventarski Broj za Karton:", "")

        if izabrani_broj:
            rezultat = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]

            if not rezultat.empty:
                # Koristimo .iloc[0] da izbegnemo grešku sa serijom podataka
                instrument = rezultat.iloc[0]
                model_instrumenta = str(instrument.get('naziv_proizvodjac', '')).strip()
                inv_broj_str = str(izabrani_broj)

                st.markdown(f"### Instrument br: **{izabrani_broj}**")
                
                tab1, tab2, tab3, tab4 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture i Opsezi", "🛠️ Servis i Provere", "📏 Etaloniranje"])

                with tab1:
                    polja = {
                        "Vrsta opreme": "vrsta_opreme", "Proizvođač": "proizvodjac", "Naziv": "naziv_proizvodjac",
                        "Serijski broj": "seriski_broj", "Datum baždarenja": "datum_bazdarenja", "Važi do": "vazi_do",
                        "Radna temperatura": "radna_temperatura", "Relativna vlažnost": "rel_vlaznost",
                        "Opseg merenja": "opseg_merenja", "Klasa tačnosti": "klasa_tacnosti", "Preciznost": "preciznost", "Podeok": "podeok"
                    }
                    popunjena = [(l, instrument[c]) for l, c in polja.items() if c in instrument and pd.notna(instrument[c]) and str(instrument[c]).strip() not in ["", "-", "nan", "None", "0"]]
                    
                    cols = st.columns(4)
                    for i, (label, val) in enumerate(popunjena):
                        with cols[i % 4]:
                            st.caption(label)
                            st.write(f"**{val}**")

                with tab2:
                    st.write(f"Kulture za model: `{model_instrumenta}`")
                    conn = get_conn()
                    # Ovde koristimo 'naziv_opreme' kao vezu u tabeli kulture_opsezi
                    df_k = pd.read_sql("SELECT kultura, min_opseg, max_opseg FROM kulture_opsezi WHERE naziv_opreme = %s", conn, params=(model_instrumenta,))
                    conn.close()
                    st.table(df_k) if not df_k.empty else st.info("Nema definisanih kultura.")

                with tab3:
                    conn = get_conn()
                    df_s = pd.read_sql("SELECT datum_servisa, opis_kvara, uradjeno FROM istorija_servisa WHERE inventarni_broj = %s", conn, params=(inv_broj_str,))
                    df_p = pd.read_sql("SELECT datum_provere, rezultat, napomena FROM istorija_provera WHERE inventarni_broj = %s", conn, params=(inv_broj_str,))
                    conn.close()
                    c1, c2 = st.columns(2)
                    with c1: 
                        st.write("Servis:")
                        st.dataframe(df_s, hide_index=True) if not df_s.empty else st.write("Nema servisa.")
                    with c2: 
                        st.write("Provere:")
                        st.dataframe(df_p, hide_index=True) if not df_p.empty else st.write("Nema provera.")

                with tab4:
                    conn = get_conn()
                    df_e = pd.read_sql("SELECT datum_etaloniranja, broj_uverenja, laboratorija, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", conn, params=(inv_broj_str,))
                    conn.close()
                    st.dataframe(df_e, use_container_width=True, hide_index=True) if not df_e.empty else st.info("Nema etaloniranja.")

            else:
                st.warning("Instrument nije pronađen.")
        else:
            st.info("Ukucaj inventarski broj levo za detalje.")

    else:
        st.warning("Baza je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
