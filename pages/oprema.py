import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# 1. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

# SIGURNOST
if not st.session_state.get('ulogovan'):
    st.info("Sesija istekla.")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje navigacije
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 2. SIDEBAR
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")

tabela_opcije = {
    "Glavna Oprema": "oprema",
    "Istorija Servisa": "istorija_servisa",
    "Etaloniranje": "istorija_etaloniranja",
    "Baždarenje": "istorija_bazdarenja",
    "Kulture": "kulture_opsezi"
}

izabrana_tabela = "oprema"
if is_admin:
    st.sidebar.header("📊 Admin Kontrole")
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]
    
    # Izvoz odmah ispod selektora
    df_exp = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_exp.empty:
        buf = io.BytesIO()
        df_exp.to_excel(buf, index=False)
        st.sidebar.download_button("📥 IZVEZI EXCEL", data=buf.getvalue(), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)

st.sidebar.markdown("---")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

# POPRAVLJENA ODJAVA (Bez switch_page koji pravi grešku)
if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.rerun()

izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
def apply_styling(df_st):
    if 'vazi_do' not in df_st.columns: return df_st
    def highlight(v):
        try:
            if pd.notnull(v) and pd.to_datetime(v).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    return df_st.style.map(highlight, subset=['vazi_do'])

# 4. GLAVNI PROGRAM
st.title(f"🔍 Pregled: {izabrana_tabela.replace('_', ' ').title()}")

try:
    df_raw = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Formatiranje datuma (samo datum bez vremena)
        for c in df.columns:
            if 'datum' in c or 'vazi_do' in c:
                df[c] = pd.to_datetime(df[c], errors='coerce').dt.date

        # REORGANIZACIJA KOLONA ZA PRIKAZ
        # Izbacujemo ID, datum_bazdarenja i ostale tehničke kolone
        za_izbacivanje = ['id', 'datum_bazdarenja', 'ima_mk', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'godina_proizvodnje', 'opseg_merenja', 'klasa_tacnosti', 'preciznost', 'podeok', 'upotreba_od', 'period_provere', 'bar_kod', 'stampac', 'status', 'zadnja_lokacija']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])

        # Preimenovanje Inventarni broj u In. broj
        if 'inventarni_broj' in df_prikaz.columns:
            df_prikaz = df_prikaz.rename(columns={'inventarni_broj': 'In. broj'})

        # Pomeranje Proizvođača ispred Naziva
        cols = list(df_prikaz.columns)
        if 'proizvodjac' in cols and 'naziv_proizvodjac' in cols:
            cols.insert(cols.index('naziv_proizvodjac'), cols.pop(cols.index('proizvodjac')))
        df_prikaz = df_prikaz[cols]

        # PRETRAGA
        pretraga = st.text_input("🔍 Pretraži tabelu:", "").lower()
        if pretraga:
            df_prikaz = df_prikaz[df_prikaz.astype(str).apply(lambda x: x.str.lower().str.contains(pretraga)).any(axis=1)]

        # PRIKAZ
        if is_admin:
            st.data_editor(apply_styling(df_prikaz), use_container_width=True, key=f"ed_{izabrana_tabela}")
        else:
            st.dataframe(apply_styling(df_prikaz), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac', '')} (Inv. br: {izabrani_broj})")
                
                # Upiti za istoriju
                ds = run_query(f"SELECT datum_servisa, broj_zapisnika, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = '{izabrani_broj}'")
                de = run_query(f"SELECT datum_etaloniranja, vazi_do, broj_sertifikata FROM istorija_etaloniranja WHERE inventarni_broj = '{izabrani_broj}'")
                db = run_query(f"SELECT datum_bazdarenja, vazi_do, broj_uverenja FROM istorija_bazdarenja WHERE inventarni_broj = '{izabrani_broj}'")

                t1, t2, t3, t4, t5 = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    detalji = [
                        ("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"),
                        ("Serijski br.", "seriski_broj"), ("Sektor", "sektor"),
                        ("Važi do", "vazi_do"), ("Upotreba od", "upotreba_od"),
                        ("Opseg", "opseg_merenja"), ("Klasa", "klasa_tacnosti"),
                        ("Preciznost", "preciznost"), ("Podeok", "podeok")
                    ]
                    c_k = st.columns(4)
                    count = 0
                    for l, k in detalji:
                        val = ins.get(k)
                        if val and str(val).strip() not in ["", "None", "nan", "-"]:
                            with c_k[count % 4]: st.metric(l, str(val))
                            count += 1
                
                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty: st.table(dk)
                
                with t3:
                    if not ds.empty: st.dataframe(ds, use_container_width=True, hide_index=True)
                    else: st.info("Nema servisa.")

                with t4:
                    if not de.empty: st.dataframe(de, use_container_width=True, hide_index=True)
                    else: st.info("Nema etaloniranja.")

                with t5:
                    if not db.empty: st.dataframe(db, use_container_width=True, hide_index=True)
                    else: st.info("Nema baždarenja.")
            else:
                st.error("Uređaj nije pronađen.")

    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Greška: {e}")
