import streamlit as st
import pandas as pd
import io
from datetime import datetime
from db_utils import run_query, get_conn

# 1. KONFIGURACIJA
st.set_page_config(page_title="Evidencija Opreme", layout="wide")

# SIGURNOST
if 'ulogovan' not in st.session_state or not st.session_state['ulogovan']:
    st.switch_page("glavna.py")
    st.stop()

is_admin = st.session_state.get('is_premium') == 5
ime_korisnika = st.session_state.get('ime_korisnika', 'Korisnik')

# Sakrivanje standardne navigacije
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

# ADMIN MENI - Vidljiv samo adminu
izabrana_tabela = "oprema"
izbor_prikaza = "Glavna Oprema"

if is_admin:
    st.sidebar.header("📊 Admin Kontrole")
    izbor_prikaza = st.sidebar.selectbox("Izaberi tabelu za rad:", list(tabela_opcije.keys()))
    izabrana_tabela = tabela_opcije[izbor_prikaza]

st.sidebar.markdown("---")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

if st.sidebar.button("🚪 Odjavi se", use_container_width=True):
    st.session_state['ulogovan'] = False
    st.switch_page("glavna.py")

st.sidebar.markdown("---")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski br. (za KARTON):", "").strip()

# 3. POMOĆNE FUNKCIJE
def apply_styling(df_st, active):
    if not active or 'vazi_do' not in df_st.columns: 
        return df_st
    
    def highlight(v):
        try:
            if pd.notnull(v) and v != "" and v != "-":
                # Pretvaramo u datum za poređenje
                val_dt = pd.to_datetime(v, errors='coerce').date()
                if val_dt and val_dt < datetime.now().date():
                    return "background-color: #ff4b4b; color: white"
        except: pass
        return ""
    
    return df_st.style.map(highlight, subset=['vazi_do'])

def export_to_excel(df_exp):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_exp.to_excel(writer, index=False)
    return output.getvalue()

# 4. GLAVNI PROGRAM
st.title(f"🔍 {izbor_prikaza}")

try:
    df = run_query(f"SELECT * FROM {izabrana_tabela}")
    if not df.empty:
        df.columns = [c.strip().lower() for c in df.columns]

        if is_admin:
            st.info(f"🔓 Mod za uređivanje: `{izabrana_tabela}`")
            # data_editor dozvoljava menjanje, dodavanje i brisanje
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"edit_{izabrana_tabela}")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 SAČUVAJ SVE IZMENE", use_container_width=True, type="primary"):
                    conn = get_conn(); cur = conn.cursor()
                    try:
                        # Brisanje i ponovni upis (najsigurnije za male tabele bez FK)
                        cur.execute(f"TRUNCATE TABLE {izabrana_tabela}") 
                        cols = edited_df.columns.tolist()
                        placeholders = ", ".join(["%s"] * len(cols))
                        sql = f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({placeholders})"
                        
                        for _, row in edited_df.iterrows():
                            vals = [None if pd.isna(row[c]) or str(row[c]) in ['nan','None',''] else row[c] for c in cols]
                            cur.execute(sql, vals)
                        
                        conn.commit()
                        st.success("Tabela uspešno osvežena u bazi!")
                        st.cache_data.clear()
                    except Exception as e: st.error(f"SQL Greška: {e}")
                    finally: conn.close()
            with c2:
                st.download_button("📥 IZVEZI U EXCEL", data=export_to_excel(df), file_name=f"{izabrana_tabela}.xlsx", use_container_width=True)
        else:
            st.dataframe(apply_styling(df, show_colors), use_container_width=True, hide_index=True)

        # --- MATIČNI KARTON ---
        if izabrani_broj and izabrana_tabela == "oprema":
            st.markdown("---")
            rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
            if not rez.empty:
                ins = rez.iloc[0]
                st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', 'Nezavedeno')}")
                t1, t2, t3, t4, t5 = st.tabs(["📋 Podaci", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
                
                with t1:
                    detalji = [("Proizvođač", "proizvodjac"), ("Model", "naziv_proizvodjac"), ("Vrsta", "vrsta_opreme"), ("Serijski br.", "seriski_broj"), ("Sektor", "sektor")]
                    cols = st.columns(len(detalji))
                    for i, (l, k) in enumerate(detalji):
                        cols[i].metric(l, ins.get(k, "-"))

                with t2:
                    m_n = str(ins.get('naziv_proizvodjac', '')).strip()
                    dk = run_query("SELECT kultura, opseg_vlage, protein FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_n.lower()}%",))
                    if not dk.empty: st.table(dk)
                    else: st.info("Nema podataka o kulturama.")

                with t3:
                    ds = run_query(f"SELECT * FROM istorija_servisa WHERE inventarni_broj = '{izabrani_broj}'")
                    if not ds.empty: st.dataframe(ds, use_container_width=True)
                    else: st.info("Nema servisa.")

                # ... i tako dalje za ostale tabove
            else:
                st.error("Nema aparata sa tim brojem.")
    else: st.warning("Tabela je prazna.")
except Exception as e: st.error(f"Greška: {e}")
