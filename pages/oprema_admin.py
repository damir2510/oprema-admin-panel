import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import io

# --- NAVIGACIJA ---
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("📋 Pregled Opreme", use_container_width=True):
    st.switch_page("pages/oprema.py")
if st.sidebar.button("📍 Mapa opreme", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

# --- Konekcija ---
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698, database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'},
        autocommit=True
    )

st.title("🛠 Admin Panel - Upravljanje Bazom")

try:
    conn = get_conn()
    df_raw = pd.read_sql("SELECT * FROM oprema", conn)
    
    if not df_raw.empty:
        df = df_raw.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        # TABOVI ZA ADMINA: UREĐIVANJE vs UVOZ/IZVOZ
        tab_edit, tab_import = st.tabs(["📝 Brza Izmena", "📥 Import/Export"])

        with tab_edit:
            st.subheader("Izmena direktno u tabeli")
            # Konfiguracija kolona (ID sakriven, ostalo editabilno)
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={"id": None},
                key="admin_editor"
            )

            if st.button("💾 SAČUVAJ IZMENE", type="primary"):
                with conn.cursor() as cursor:
                    for _, row in edited_df.iterrows():
                        sql = """UPDATE oprema SET sektor=%s, vrsta_opreme=%s, proizvodjac=%s, 
                                 naziv_proizvodjac=%s, status=%s, napomena=%s WHERE id=%s"""
                        cursor.execute(sql, (row['sektor'], row['vrsta_opreme'], row['proizvodjac'],
                                           row['naziv_proizvodjac'], row['status'], row['napomena'], row['id']))
                st.success("Baza je uspešno ažurirana!")
                st.rerun()

        with tab_import:
            st.subheader("Rad sa Excel fajlovima")
            
            # --- EXPORT ---
            st.write("1. Preuzmi trenutno stanje:")
            output = io.BytesIO()
            # Ovde se dešava greška ako nema openpyxl-a
            df.to_excel(output, index=False, engine='openpyxl')
            st.download_button("📥 Preuzmi bazu (Excel)", output.getvalue(), "admin_export.xlsx")

            st.divider()

            # --- IMPORT ---
            st.write("2. Ubaci nove podatke (Excel):")
            uploaded_file = st.file_uploader("Izaberi Excel fajl", type=["xlsx"])
            if uploaded_file:
                df_upload = pd.read_excel(uploaded_file, engine='openpyxl')
                st.write("Pregled fajla za uvoz:")
                st.dataframe(df_upload.head(3))
                if st.button("🚀 Potvrdi uvoz u bazu"):
                    # Ovde bi išla logika za INSERT (ako želiš masovni uvoz)
                    st.warning("Funkcija uvoza zahteva precizno mapiranje kolona.")

    conn.close()
except Exception as e:
    st.error(f"Sistemska greška: {e}")
