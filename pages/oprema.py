import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# --- KONFIGURACIJA ---
st.set_page_config(page_title="Sektor Opreme", layout="wide", page_icon="🔍")

# 1. DEFINISANJE STRANICA (Da bi switch_page radio unutar navigation sistema)
p_mapa = st.Page("pages/mapa_opreme.py")
p_admin = st.Page("pages/oprema_admin.py")

# 2. FUNKCIJA ZA BAZU
def run_query(query, params=None):
    try:
        conn = pymysql.connect(
            host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
            user="avnadmin",
            password="AVNS_0qoNdSQVUuF9wTfHN8D",
            port=27698,
            database="defaultdb",
            cursorclass=pymysql.cursors.DictCursor,
            ssl={'ssl-mode': 'REQUIRED'}
        )
        with conn.cursor() as cur:
            cur.execute(query, params)
            return pd.DataFrame(cur.fetchall())
    except Exception as e:
        st.error(f"Greška: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals(): conn.close()

# --- SIDEBAR NAVIGACIJA ---
st.sidebar.header("🚀 Brze akcije")

# Korišćenje Page objekata osigurava da Streamlit ne izbaci grešku
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page(p_mapa)

if st.sidebar.button("🔐 Admin Panel", use_container_width=True):
    st.switch_page(p_admin)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filteri")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj (za karton):", "").strip()

# --- GLAVNI SADRŽAJ ---
st.title("🔍 Evidencija i Pregled Opreme")

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Sređivanje datuma
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # REORGANIZACIJA TABELE
        fiksne_prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac']
        fiksne_zadnje = ['putanja_folder', 'zadnja_lokacija', 'status', 'napomena']
        izbaci = ['id', 'inventarni_broj', 'stampac', 'gps_koordinate', 'ima_mk', 'period_provere', 
                  'godina_proizvodnje', 'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 
                  'radna_temperatura', 'klasa_tacnosti', 'preciznost', 'podeok', 'lokacija']
        
        preostale = [c for c in df.columns if c not in fiksne_prve and c not in fiksne_zadnje and c not in izbaci]
        novi_poredak = fiksne_prve + preostale + fiksne_zadnje
        main_display = df[[c for c in novi_poredak if c in df.columns]]

        # Funkcija za bojenje
        def apply_styling(df_st, active):
            if not active or 'vazi_do' not in df_st.columns: return df_st
            return df_st.style.applymap(lambda v: "background-color: #ff4b4b; color: white" if pd.notnull(v) and v < datetime.now().date() else "", subset=['vazi_do'])

        st.dataframe(apply_styling(main_display, show_colors), use_container_width=True, hide_index=True)
        st.write("---")

        # MATIČNI KARTON
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', '')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    svi_potencijalni = [
                        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
                        ("Vrsta", "vrsta_opreme"), ("Serijski br.", "seriski_broj"),
                        ("Opseg merenja", "opseg_merenja"), ("U upotrebi od", "upotreba_od")
                    ]
                    cols = st.columns(4)
                    i = 0
                    for label, key in svi_potencijalni:
                        val = ins.get(key)
                        if str(val).strip() not in ["", "None", "nan", "-"]:
                            with cols[i % 4]:
                                st.write(f"**{label}**")
                                st.info(val)
                            i += 1
                
                # ... ostatak tabova (t2-t5) ostaje isti kao u prethodnom kodu ...
                with t2:
                    m_name = str(ins.get('naziv_proizvodjac', '')).strip()
                    df_k = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_name.lower()}%",))
                    st.table(df_k.fillna("-")) if not df_k.empty else st.warning("Nema podataka.")
                with t3:
                    df_s = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.dataframe(df_s, use_container_width=True, hide_index=True) if not df_s.empty else st.info("Nema servisa.")
                with t4:
                    df_e = run_query("SELECT datum_etaloniranja, broj_sertifikata, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.dataframe(df_e, use_container_width=True, hide_index=True) if not df_e.empty else st.info("Nema etaloniranja.")
                with t5:
                    df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    st.dataframe(df_b, use_container_width=True, hide_index=True) if not df_b.empty else st.info("Nema baždarenja.")

    else:
        st.warning("Baza je prazna.")
except Exception as e:
    st.error(f"Sistemska greška: {e}")
