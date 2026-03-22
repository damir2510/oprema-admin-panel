import streamlit as st
import pandas as pd
from datetime import datetime
from db_utils import run_query 

# --- 1. KONFIGURACIJA (Široki ekran i sakrivanje menija) ---
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] ul { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DEFINICIJA STRANICA ZA NAVIGACIJU ---
p_mapa = st.Page("pages/mapa_opreme.py")
p_admin = st.Page("pages/oprema_admin.py")

st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("🗺️ Mapa opreme", use_container_width=True):
    st.switch_page(p_mapa)

if st.sidebar.button("🛠️ Admin Panel", use_container_width=True):
    st.switch_page(p_admin)

st.sidebar.markdown("---")

# 3. POMOĆNE FUNKCIJE
def ima_podatak(val):
    return str(val).strip() not in ["", "None", "nan", "-", "0", "NoneType"]

def apply_styling(df, should_highlight):
    if not should_highlight or 'vazi_do' not in df.columns:
        return df
    def highlight_logic(val):
        if pd.isna(val) or val == "" or val == "-": return ""
        try:
            if pd.to_datetime(val).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    return df.style.applymap(highlight_logic, subset=['vazi_do'])

# --- GLAVNI SADRŽAJ ---
st.title("🔍 Evidencija Opreme")

st.sidebar.header("⚙️ Kontrole")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj (za karton):", "").strip()

try:
    df_raw = run_query("SELECT * FROM oprema")
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # Čišćenje datuma
        for col in ['vazi_do', 'datum_bazdarenja', 'datum_kontrole']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        # REORGANIZACIJA KOLONA
        fiksne_prve = ['sektor', 'vrsta_opreme', 'proizvodjac', 'naziv_proizvodjac']
        fiksne_zadnje = ['putanja_folder', 'zadnja_lokacija', 'status', 'napomena']
        izbaci = ['id', 'inventarni_broj', 'stampac', 'gps_koordinate', 'ima_mk', 'period_provere', 
                  'godina_proizvodnje', 'upotreba_od', 'rel_vlaznost', 'opseg_merenja', 
                  'radna_temperatura', 'klasa_tacnosti', 'preciznost', 'podeok', 'lokacija']
        
        preostale = [c for c in df.columns if c not in fiksne_prve and c not in fiksne_zadnje and c not in izbaci]
        novi_poredak = fiksne_prve + preostale + fiksne_zadnje
        main_display = df[[c for c in novi_poredak if c in df.columns]]

        # Prikaz glavne tabele - SADA PREKO CELOG EKRANA
        st.dataframe(apply_styling(main_display, show_colors), use_container_width=True, hide_index=True)
        st.write("---")

        # --- MATIČNI KARTON ---
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', '')} | {ins.get('vrsta_opreme', '')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])

                with t1:
                    svi_potencijalni = [
                        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
                        ("Vrsta", "vrsta_opreme"), ("Serijski br.", "seriski_broj"),
                        ("Opseg merenja", "opseg_merenja"), ("Klasa tačnosti", "klasa_tacnosti"),
                        ("Preciznost (d)", "preciznost"), ("Overeni podeok (e)", "podeok"),
                        ("Radna Temperatura", "radna_temperatura"), ("Rel. Vlažnost", "rel_vlaznost"),
                        ("Godina proizvodnje", "godina_proizvodnje"), ("U upotrebi od", "upotreba_od")
                    ]
                    podaci_za_prikaz = [(l, ins.get(k)) for l, k in svi_potencijalni if ima_podatak(ins.get(k))]
                    
                    cols = st.columns(4)
                    for i, (label, val) in enumerate(podaci_za_prikaz):
                        with cols[i % 4]:
                            st.write(f"**{label}**")
                            st.info(val)

                with t2:
                    m_name = str(ins.get('naziv_proizvodjac', '')).strip()
                    df_k = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_name.lower()}%",))
                    if not df_k.empty:
                        st.table(df_k.fillna("-"))
                    else:
                        st.warning("Nema podataka o kulturama.")
                
                with t3:
                    df_s = run_query("SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_s.empty:
                        st.dataframe(df_s, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema servisa.")
                
                with t4:
                    df_e = run_query("SELECT datum_etaloniranja, broj_sertifikata, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_e.empty:
                        st.dataframe(df_e, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema etaloniranja.")
                
                with t5:
                    df_b = run_query("SELECT datum_bazdarenja, broj_uverenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not df_b.empty:
                        st.dataframe(df_b, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nema baždarenja.")
            else:
                st.sidebar.error("Instrument nije pronađen!")
    else:
        st.warning("Baza podataka je prazna.")
except Exception as e:
    st.error(f"Sistemska greška: {e}")
