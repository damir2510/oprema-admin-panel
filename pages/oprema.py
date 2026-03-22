import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. SIGURNOSNA PROVERA LOGOVANJA
if not st.session_state.get('ulogovan'):
    st.switch_page("glavna.py")

# 2. KONFIGURACIJA STRANE
st.set_page_config(page_title="Sektor Opreme", layout="wide")

# Provera nivoa pristupa
is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije (rakete)
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 3. SIDEBAR NAVIGACIJA I KONTROLE
st.sidebar.markdown(f"👤 Prijavljeni ste kao: **{ime_korisnika}**")
st.sidebar.header("🚀 Navigacija")
p_pocetna = st.Page("glavna.py")
p_mapa = st.Page("pages/mapa_opreme.py")

if st.sidebar.button("🏠 Početna", use_container_width=True):
    st.switch_page(p_pocetna)
if st.sidebar.button("🗺️ Mapa lokacija", use_container_width=True):
    st.switch_page(p_mapa)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Odjavi se", use_container_width=True, type="secondary"):
    st.session_state['ulogovan'] = False
    st.session_state['is_premium'] = 0
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filteri prikaza")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj (Karton):", "").strip()

# 4. POMOĆNE FUNKCIJE
def apply_styling(df_st, active):
    if not active or 'vazi_do' not in df_st.columns: return df_st
    return df_st.style.applymap(lambda v: "background-color: #ff4b4b; color: white" if pd.notnull(v) and v < datetime.now().date() else "", subset=['vazi_do'])

def export_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Oprema')
    return output.getvalue()

# 5. GLAVNI PROGRAM
st.title("🔍 Centralna Evidencija Opreme")

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        
        # Filtriranje onih koji nisu pravi podaci (ako se zaglavlje ponovilo)
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # --- ADMIN MOD (UREĐIVANJE) ---
        if is_admin:
            st.info(f"🔓 **ADMIN MOD AKTIVAN:** Dobrodošli {ime_korisnika}. Ovde možete menjati bazu.")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=False, key="admin_editor")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ SVE IZMENE U SQL BAZU", use_container_width=True, type="primary"):
                    conn = get_conn(); cur = conn.cursor()
                    state = st.session_state["admin_editor"]
                    try:
                        # Brisanje redova
                        if state['deleted_rows']:
                            for idx in state['deleted_rows']:
                                row_id = df.iloc[idx]['id']
                                cur.execute("DELETE FROM oprema WHERE id = %s", (int(row_id),))
                        # Unos/Izmena
                        for _, row in edited_df.iterrows():
                            sql_cols = [c for c in edited_df.columns if c != 'id']
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['-', 'nan', 'None'] else row[c] for c in sql_cols]
                            if not pd.isna(row.get('id')) and str(row.get('id')) != '':
                                cur.execute(f"UPDATE oprema SET {', '.join([f'{c}=%s' for c in sql_cols])} WHERE id=%s", vals + [int(row['id'])])
                            else:
                                cur.execute(f"INSERT INTO oprema ({', '.join(sql_cols)}) VALUES ({', '.join(['%s']*len(sql_cols))})", vals)
                        conn.commit(); st.success("Baza uspešno ažurirana!"); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Greška prilikom snimanja: {e}")
                    finally: conn.close()
            with c2:
                st.download_button("📥 PREUZMI EXCEL", data=export_to_excel(df), file_name="oprema.xlsx", use_container_width=True)

        # --- KORISNIČKI MOD (SAMO PREGLED) ---
        else:
            st.write(f"👋 Dobrodošli, {ime_korisnika}. Pregledate listu opreme.")
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- MATIČNI KARTON ---
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                # Koristimo iloc[0] da dobijemo konkretan red
                ins = rez.iloc[0]
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', '')}")
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    svi = [("Vrsta", "vrsta_opreme"), ("Model", "naziv_proizvodjac"), ("Serijski", "seriski_broj"), ("Sektor", "sektor")]
                    cols = st.columns(4)
                    for i, (l, k) in enumerate(svi):
                        val = ins.get(k, "-")
                        with cols[i%4]: st.metric(l, val if pd.notnull(val) else "-")
                
                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty: st.table(dk)
                    else: st.warning("Nema definisanih kultura za ovaj model.")
                
                with t3:
                    ds = run_query("SELECT datum_servisa, opis_intervencije FROM istorija_servisa WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not ds.empty: st.dataframe(ds, use_container_width=True, hide_index=True)
                    else: st.info("Nema zabeleženih servisa.")
                
                with t4:
                    de = run_query("SELECT datum_etaloniranja, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not de.empty: st.dataframe(de, use_container_width=True, hide_index=True)
                    else: st.info("Nema podataka o etaloniranju.")

                with t5:
                    db = run_query("SELECT datum_bazdarenja, vazi_do FROM istorija_bazdarenja WHERE inventarni_broj = %s", (izabrani_broj,))
                    if not db.empty: st.dataframe(db, use_container_width=True, hide_index=True)
                    else: st.info("Nema podataka o baždarenju.")
            else:
                st.sidebar.error("Instrument nije pronađen!")

    else: st.warning("Baza podataka je prazna.")
except Exception as e: 
    st.error(f"Sistemska greška: {e}")
