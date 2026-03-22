import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. SIGURNOSNA PROVERA LOGOVANJA
if not st.session_state.get('ulogovan'):
    st.switch_page(import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. SIGURNOSNA PROVERA LOGOVANJA
# Ako korisnik nije ulogovan, samo osvežavamo stranu - glavna.py će ga detektovati i vratiti na login
if not st.session_state.get('ulogovan'):
    st.rerun()

# 2. KONFIGURACIJA STRANE
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

# Podaci iz sesije
is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije (rakete)
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 3. SIDEBAR NAVIGACIJA I KONTROLE
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")
st.sidebar.header("🚀 Navigacija")

# Koristimo direktne putanje ka fajlovima
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.session_state['is_premium'] = 0
    st.rerun() # Sigurnije od switch_page za glavni fajl

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filteri prikaza")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 4. POMOĆNE FUNKCIJE
def apply_styling(df_st, active):
    if not active or 'vazi_do' not in df_st.columns: 
        return df_st
    def highlight(v):
        try:
            if pd.notnull(v) and pd.to_datetime(v).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: 
            pass
        return ""
    return df_st.style.applymap(highlight, subset=['vazi_do'])

def export_to_excel(df_exp):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_exp.to_excel(writer, index=False, sheet_name='Oprema')
    return output.getvalue()

# 5. GLAVNI PROGRAM
st.title("🔍 Centralna Evidencija Opreme")

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        # Čišćenje ako su zaglavlja upisana kao podaci
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # --- ADMIN MOD (UREĐIVANJE) ---
        if is_admin:
            st.info(f"🔓 **ADMIN MOD AKTIVAN**")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=False, key="admin_editor")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ SVE IZMENE", use_container_width=True, type="primary"):
                    conn = get_conn()
                    cur = conn.cursor()
                    state = st.session_state["admin_editor"]
                    try:
                        # Brisanje redova
                        if state.get('deleted_rows'):
                            for idx in state['deleted_rows']:
                                row_id = df.iloc[idx]['id']
                                cur.execute("DELETE FROM oprema WHERE id = %s", (int(row_id),))
                        
                        # Update i Insert
                        for _, row in edited_df.iterrows():
                            sql_cols = [c for c in edited_df.columns if c != 'id']
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['-', 'nan', 'None', ''] else row[c] for c in sql_cols]
                            
                            if not pd.isna(row.get('id')) and str(row.get('id')) != '':
                                set_clause = ", ".join([f"{c}=%s" for c in sql_cols])
                                cur.execute(f"UPDATE oprema SET {set_clause} WHERE id=%s", vals + [int(row['id'])])
                            else:
                                col_names = ", ".join(sql_cols)
                                placeholders = ", ".join(['%s'] * len(sql_cols))
                                cur.execute(f"INSERT INTO oprema ({col_names}) VALUES ({placeholders})", vals)
                        
                        conn.commit()
                        st.success("Baza uspešno ažurirana!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Greška pri čuvanju: {e}")
                    finally: 
                        conn.close()
            with c2:
                st.download_button("📥 PREUZMI EXCEL", data=export_to_excel(df), file_name="oprema.xlsx", use_container_width=True)

        # --- KORISNIČKI MOD (SAMO PREGLED) ---
        else:
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- MATIČNI KARTON ---
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Matični karton: {ins.get('naziv_proizvodjac', 'Nezavedeno')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    detalji = [
                        ("🏭 Proizvođač", "proizvodjac"), ("📦 Model", "naziv_proizvodjac"),
                        ("🔧 Vrsta", "vrsta_opreme"), ("🔢 Serijski br.", "seriski_broj"),
                        ("📍 Sektor", "sektor"), ("📅 U upotrebi od", "upotreba_od"),
                        ("📏 Opseg merenja", "opseg_merenja"), ("🎯 Klasa tačnosti", "klasa_tacnosti"),
                        ("⚖ Preciznost (d)", "preciznost"), ("🔘 Podeok (e)", "podeok"),
                        ("🌡️ Radna Temp.", "radna_temperatura"), ("💧 Rel. Vlažnost", "rel_vlaznost")
                    ]
                    cols = st.columns(4)
                    count = 0
                    for label, key in detalji:
                        val = ins.get(key)
                        if val and str(val).strip() not in ["", "None", "nan", "-", "0"]:
                            with cols[count % 4]:
                                st.markdown(f"<p style='color: gray; font-size: 0.85em; margin-bottom: -5px;'>{label}</p>", unsafe_allow_html=True)
                                st.info(val)
                            count += 1
                
                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty:
                        st.table(dk)
                    else:
                        st.warning("Nema podataka o kulturama.")
                
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
                st.error(f"Instrument sa brojem {izabrani_broj} nije pronađen!")

    else: 
        st.warning("Baza podataka je prazna.")
except Exception as e: 
    st.error(f"Sistemska greška: {e}")
"glavna.py")

# 2. KONFIGURACIJA STRANE
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

# Podaci iz sesije
is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije (rakete)
st.markdown("""<style>[data-testid="stSidebarNav"] ul { display: none; }</style>""", unsafe_allow_html=True)

# 3. SIDEBAR NAVIGACIJA I KONTROLE
st.sidebar.markdown(f"👤 Prijavljeni: **{ime_korisnika}**")
st.sidebar.header("🚀 Navigacija")

if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.session_state['is_premium'] = 0
    st.switch_page("glavna.py")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filteri prikaza")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 4. POMOĆNE FUNKCIJE
def apply_styling(df_st, active):
    if not active or 'vazi_do' not in df_st.columns: 
        return df_st
    def highlight(v):
        try:
            if pd.notnull(v) and pd.to_datetime(v).date() < datetime.now().date():
                return "background-color: #ff4b4b; color: white"
        except: 
            pass
        return ""
    return df_st.style.applymap(highlight, subset=['vazi_do'])

def export_to_excel(df_exp):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_exp.to_excel(writer, index=False, sheet_name='Oprema')
    return output.getvalue()

# 5. GLAVNI PROGRAM
st.title("🔍 Centralna Evidencija Opreme")

try:
    df_raw = run_query("SELECT * FROM oprema")
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]
        # Čišćenje duplih hedera ako postoje u bazi
        df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']

        # --- ADMIN MOD (UREĐIVANJE) ---
        if is_admin:
            st.info(f"🔓 **ADMIN MOD AKTIVAN**")
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=False, key="admin_editor")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ SVE IZMENE", use_container_width=True, type="primary"):
                    conn = get_conn()
                    cur = conn.cursor()
                    state = st.session_state["admin_editor"]
                    try:
                        # Brisanje redova
                        if state.get('deleted_rows'):
                            for idx in state['deleted_rows']:
                                row_id = df.iloc[idx]['id']
                                cur.execute("DELETE FROM oprema WHERE id = %s", (int(row_id),))
                        
                        # Update i Insert
                        for _, row in edited_df.iterrows():
                            sql_cols = [c for c in edited_df.columns if c != 'id']
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['-', 'nan', 'None', ''] else row[c] for c in sql_cols]
                            
                            if not pd.isna(row.get('id')) and str(row.get('id')) != '':
                                set_clause = ", ".join([f"{c}=%s" for c in sql_cols])
                                cur.execute(f"UPDATE oprema SET {set_clause} WHERE id=%s", vals + [int(row['id'])])
                            else:
                                col_names = ", ".join(sql_cols)
                                placeholders = ", ".join(['%s'] * len(sql_cols))
                                cur.execute(f"INSERT INTO oprema ({col_names}) VALUES ({placeholders})", vals)
                        
                        conn.commit()
                        st.success("Baza uspešno ažurirana!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Greška pri čuvanju: {e}")
                    finally: 
                        conn.close()
            with c2:
                st.download_button("📥 PREUZMI EXCEL", data=export_to_excel(df), file_name="oprema.xlsx", use_container_width=True)

        # --- KORISNIČKI MOD (SAMO PREGLED) ---
        else:
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- MATIČNI KARTON ---
        if izabrani_broj:
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Matični karton: {ins.get('naziv_proizvodjac', 'Nezavedeno')}")
                
                t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    detalji = [
                        ("🏭 Proizvođač", "proizvodjac"), ("📦 Model", "naziv_proizvodjac"),
                        ("🔧 Vrsta", "vrsta_opreme"), ("🔢 Serijski br.", "seriski_broj"),
                        ("📍 Sektor", "sektor"), ("📅 U upotrebi od", "upotreba_od"),
                        ("📏 Opseg merenja", "opseg_merenja"), ("🎯 Klasa tačnosti", "klasa_tacnosti"),
                        ("⚖ Preciznost (d)", "preciznost"), ("🔘 Podeok (e)", "podeok"),
                        ("🌡️ Radna Temp.", "radna_temperatura"), ("💧 Rel. Vlažnost", "rel_vlaznost")
                    ]
                    cols = st.columns(4)
                    count = 0
                    for label, key in detalji:
                        val = ins.get(key)
                        if val and str(val).strip() not in ["", "None", "nan", "-", "0"]:
                            with cols[count % 4]:
                                st.markdown(f"<p style='color: gray; font-size: 0.85em; margin-bottom: -5px;'>{label}</p>", unsafe_allow_html=True)
                                st.info(val)
                            count += 1
                
                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty:
                        st.table(dk)
                    else:
                        st.warning("Nema podataka o kulturama.")
                
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
                st.error(f"Instrument sa brojem {izabrani_broj} nije pronađen!")

    else: 
        st.warning("Baza podataka je prazna.")
except Exception as e: 
    st.error(f"Sistemska greška: {e}")
