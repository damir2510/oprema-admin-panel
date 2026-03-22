import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

if not st.session_state.get('ulogovan'):
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

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
izbor_prikaza = "Glavna Oprema"

if is_admin:
    st.sidebar.header("📊 Admin Kontrole")
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]

    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Uvoz podataka")
    uploaded_file = st.sidebar.file_uploader(f"Uvezi Excel u {izabrana_tabela}", type=["xlsx"])
    if uploaded_file and st.sidebar.button("🚀 POKRENI UVOZ", use_container_width=True):
        try:
            new_data = pd.read_excel(uploaded_file)
            conn = get_conn(); cur = conn.cursor()
            cur.execute(f"TRUNCATE TABLE {izabrana_tabela}")
            cols = [c.strip().lower() for c in new_data.columns]
            placeholders = ", ".join(["%s"] * len(cols))
            for _, row in new_data.iterrows():
                cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({placeholders})", list(row))
            conn.commit(); conn.close()
            st.sidebar.success("Podaci uspešno uvezeni!")
            st.cache_data.clear(); st.rerun()
        except Exception as e: st.sidebar.error(f"Greška pri uvozu: {e}")

st.sidebar.markdown("---")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.switch_page("glavna.py")

izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
def apply_styling(df_st):
    if 'vazi_do' not in df_st.columns: return df_st
    def highlight(v):
        try:
            if pd.notnull(v) and pd.to_datetime(v, errors='coerce').date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    return df_st.style.map(highlight, subset=['vazi_do'])

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_prikaza}")

try:
    df = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

        # Filter kolona za tabelarni prikaz
        za_izbacivanje = ['ima_mk', 'gps_koordinate', 'radna_temperatura', 'rel_vlaznost', 'godina_proizvodnje', 'opseg_merenja', 'klasa_tacnosti', 'preciznost', 'podeok', 'upotreba_od', 'period_provere', 'bar_kod', 'stampac', 'status']
        df_prikaz = df.drop(columns=[c for c in za_izbacivanje if c in df.columns])

        if is_admin:
            st.data_editor(df_prikaz, use_container_width=True, key=f"ed_{izabrana_tabela}")
            st.download_button("📥 IZVEZI U EXCEL", data=io.BytesIO().getvalue(), file_name=f"{izabrana_tabela}.xlsx")
        else:
            st.dataframe(apply_styling(df_prikaz), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                
                # Zaglavlje kartona sa ikonicom
                st.subheader(f"📑 Karton: {ins.get('naziv_proizvodjac', '')} (Inv. br: {izabrani_broj})")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    # Dodate kolone: upotreba_od, period_provere
                    detalji = [
                        ("🏭 Proizvođač", "proizvodjac"), ("📦 Model", "naziv_proizvodjac"),
                        ("🔢 Serijski br.", "seriski_broj"), ("📅 Godina pr.", "godina_proizvodnje"),
                        ("📍 Sektor", "sektor"), ("📅 Važi do", "vazi_do"),
                        ("📏 Opseg", "opseg_merenja"), ("🎯 Klasa", "klasa_tacnosti"),
                        ("⚖ Preciznost", "preciznost"), ("🔘 Podeok", "podeok"),
                        ("🌡️ Temp.", "radna_temperatura"), ("💧 Vlažnost", "rel_vlaznost"),
                        ("⏳ Upotreba od", "upotreba_od"), ("🔄 Period provere", "period_provere")
                    ]
                    cols = st.columns(4)
                    for i, (l, k) in enumerate(detalji):
                        val = ins.get(k, "-")
                        with cols[i % 4]:
                            st.metric(label=l, value=str(val))

                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty:
                        st.table(dk)
                    else:
                        st.info("Nema podataka o kulturama.")

                with t3:
                    ds = run_query("SELECT datum_servisa, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not ds.empty:
                        st.dataframe(ds, use_container_width=True)
                    else:
                        st.info("Nema zabeleženih servisa.")

                with t4:
                    de = run_query("SELECT datum_etaloniranja, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not de.empty:
                        st.dataframe(de, use_container_width=True)
                    else:
                        st.info("Nema podataka o etaloniranju.")

                with t5:
                    db = run_query("SELECT datum_bazdarenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not db.empty:
                        st.dataframe(db, use_container_width=True)
                    else:
                        st.info("Nema podataka o baždarenju.")
            else:
                st.error(f"Uređaj sa inventarnim brojem {izabrani_broj} nije pronađen.")
    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Sistemska greška: {e}")
