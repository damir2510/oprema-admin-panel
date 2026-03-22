import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

if not st.session_state.get('ulogovan'):
    st.rerun()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje raketa
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 2. SIDEBAR - ADMIN KONTROLE NA VRHU
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")

# Logika za promenu tabela (Samo za Admina)
tabela_opcije = {
    "Glavna Oprema": "oprema",
    "Istorija Servisa": "istorija_servisa",
    "Etaloniranje": "istorija_etaloniranja",
    "Baždarenje": "istorija_bazdarenja",
    "Kulture": "kulture_opsezi"
}

if is_admin:
    st.sidebar.header("📊 Admin: Izbor tabele")
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu za rad/izvoz:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]
else:
    izabrana_tabela = "oprema"
    izbor_prikaza = "Glavna Oprema"

st.sidebar.markdown("---")
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.rerun()

st.sidebar.markdown("---")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
def apply_styling(df_st, active):
    if not active or 'vazi_do' not in df_st.columns: 
        return df_st
    def highlight(v):
        try:
            if pd.notnull(v):
                # Provera datuma
                val_dt = pd.to_datetime(v).date()
                if val_dt < datetime.now().date():
                    return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    # Streamlit 1.30+ koristi .map() umesto .applymap()
    return df_st.style.map(highlight, subset=['vazi_do'])

def export_to_excel(df_exp, name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_exp.to_excel(writer, index=False, sheet_name='Podaci')
    return output.getvalue()

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_prikaza}")

try:
    df_raw = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        if is_admin:
            st.info(f"🔓 Admin mod: Uređivanje tabele `{izabrana_tabela}`")
            # Dinamički editor sa ključem tabele
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"ed_{izabrana_tabela}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ IZMENE", use_container_width=True, type="primary"):
                    conn = get_conn(); cur = conn.cursor()
                    try:
                        cur.execute(f"DELETE FROM {izabrana_tabela}")
                        cols = edited_df.columns.tolist()
                        for _, row in edited_df.iterrows():
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['nan','None',''] else row[c] for c in cols]
                            cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))})", vals)
                        conn.commit()
                        st.success("Baza ažurirana!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Greška: {e}")
                    finally: conn.close()
            with c2:
                st.download_button("📥 PREUZMI EXCEL", data=export_to_excel(df, izabrana_tabela), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)
        else:
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            
            if not rez.empty:
                ins = rez.iloc[0] # Uzimamo prvi red kao Series
                st.subheader(f"📄 Matični karton: {ins.get('naziv_proizvodjac', 'Nezavedeno')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    detalji = [
                        ("🏭 Proizvođač", "proizvodjac"), ("📦 Model", "naziv_proizvodjac"),
                        ("🔧 Vrsta", "vrsta_opreme"), ("🔢 Serijski br.", "seriski_broj"),
                        ("📍 Sektor", "sektor"), ("📅 U upotrebi od", "upotreba_od"),
                        ("📏 Opseg merenja", "opseg_merenja"), ("🎯 Klasa tačnosti", "klasa_tacnosti"),
                        ("⚖ Preciznost (d)", "preciznost"), ("🔘 Podeok (e)", "podeok")
                    ]
                    cols = st.columns(4)
                    for i, (label, key) in enumerate(detalji):
                        val = ins.get(key)
                        if val and str(val).strip() not in ["", "None", "nan", "-"]:
                            with cols[i % 4]:
                                st.caption(label)
                                st.info(val)

                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty: st.table(dk)
                    else: st.warning("Nema podataka o kulturama.")

                # Popravka za Servis, Etalon, Bazdarenje (bez DeltaGenerator greške)
                with t3:
                    ds = run_query(f"SELECT * FROM istorija_servisa WHERE inventarni_broj = '{izabrani_broj}'")
                    if not ds.empty: st.dataframe(ds, use_container_width=True)
                    else: st.info("Nema podataka.")

                with t4:
                    de = run_query(f"SELECT * FROM istorija_etaloniranja WHERE inventarni_broj = '{izabrani_broj}'")
                    if not de.empty: st.dataframe(de, use_container_width=True)
                    else: st.info("Nema podataka.")

                with t5:
                    db = run_query(f"SELECT * FROM istorija_bazdarenja WHERE inventarni_broj = '{izabrani_broj}'")
                    if not db.empty: st.dataframe(db, use_container_width=True)
                    else: st.info("Nema podataka.")
            else:
                st.error("Instrument nije pronađen.")
    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Greška: {e}")
