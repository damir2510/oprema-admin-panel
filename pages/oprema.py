import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime

# --- UKLONJEN set_page_config (on je sada u glavna.py) ---

# 1. DEFINICIJA STRANICA (Mora biti ista kao u glavna.py da bi switch radio)
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
        st.error(f"Baza greška: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals(): conn.close()

# --- SIDEBAR NAVIGACIJA ---
st.sidebar.header("🚀 Brze akcije")
if st.sidebar.button("🗺️ Otvori Mapu", use_container_width=True):
    st.switch_page(p_mapa) # Koristimo OBJEKAT, ne string

if st.sidebar.button("🔐 Admin Panel", use_container_width=True):
    st.switch_page(p_admin) # Koristimo OBJEKAT, ne string

st.sidebar.markdown("---")
show_colors = st.sidebar.toggle("Prikaži istekle (boje)", value=True)
izabrani_broj = st.sidebar.text_input("🔢 Inventarski Broj:", "").strip()

st.title("🔍 Pregled Opreme")

# --- PRIKAZ TABELE ---
df_raw = run_query("SELECT * FROM oprema")
if not df_raw.empty:
    df = df_raw.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Glavna tabela (pojednostavljeno za test)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- MATIČNI KARTON (Popravljena logika) ---
    if izabrani_broj:
        rez = df[df['inventarni_broj'].astype(str).str.strip() == izabrani_broj]
        if not rez.empty:
            ins = rez.iloc[0] # VAŽNO: Dodato [0] da bi dobili Series objekt
            st.subheader(f"📄 Karton: {ins.get('naziv_proizvodjac', 'N/A')}")
            
            t1, t2, t3, t4, t5 = st.tabs(["📋 Osnovno", "🌾 Kulture", "🛠 Servis", "📏 Etalon", "⚖ Baždarenje"])
            
            with t1:
                st.info(f"Model: {ins.get('naziv_proizvodjac')}")
                st.write(f"Sektor: {ins.get('sektor')}")
            
            with t2:
                m_name = str(ins.get('naziv_proizvodjac', '')).strip()
                df_k = run_query("SELECT kultura, opseg_vlage FROM kulture_opsezi WHERE LOWER(naziv_proizvodjac) LIKE %s", (f"%{m_name.lower()}%",))
                if not df_k.empty: st.table(df_k)
                else: st.warning("Nema podataka.")
            
            # ... ponoviti istu logiku za t3, t4, t5 ...
        else:
            st.error("Broj nije pronađen.")
