import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import io

# --- 1. NAVIGACIJA ---
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("📋 Pregled Opreme", use_container_width=True):
    st.switch_page("pages/oprema.py")
if st.sidebar.button("📍 Mapa opreme", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

# --- 2. KONEKCIJA ---
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698, database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'},
        autocommit=True
    )

st.title("🛠 Admin Panel - Upravljanje Bazama")

# --- 3. IZBOR TABELE (Vraćeno biranje) ---
tabela_za_rad = st.selectbox("Izaberi tabelu za rad:", 
                            ["oprema", "istorija_servisa", "istorija_etaloniranja", "istorija_bazdarenja", "kulture_opsezi"])

try:
    conn = get_conn()
    df_raw = pd.read_sql(f"SELECT * FROM `{tabela_za_rad}`", conn)
    
    if not df_raw.empty:
        df = df_raw.copy()
        
        # Čišćenje: Brišemo red samo ako je identičan nazivu bilo koje kolone
        # Ovo sprečava "praznu tabelu" ako su podaci ispravni
        for col in df.columns:
            df = df[df[col].astype(str).str.lower() != str(col).lower()]

        tab_edit, tab_io = st.tabs(["📝 Brza Izmena", "📥 Import/Export"])

        with tab_edit:
            st.subheader(f"Uređivanje: {tabela_za_rad}")
            
            # Dinamički prikaz: Sve kolone su vidljive i tabela je ŠIROKA
            edited_df = st.data_editor(
                df,
                use_container_width=True, 
                hide_index=True,
                column_config={"id": None}, # Sakrivamo ID, ali je tu za UPDATE
                key=f"editor_{tabela_za_rad}",
                height=500
            )

            if st.button("💾 SAČUVAJ IZMENE U BAZU", type="primary"):
                with conn.cursor() as cursor:
                    kolone = [c for c in edited_df.columns if c != 'id']
                    set_clause = ", ".join([f"`{c}`=%s" for c in kolone])
                    sql = f"UPDATE `{tabela_za_rad}` SET {set_clause} WHERE id=%s"
                    
                    for _, row in edited_df.iterrows():
                        # Priprema vrednosti (None za prazna polja)
                        values = [None if pd.isna(row[c]) else row[c] for c in kolone] + [row['id']]
                        cursor.execute(sql, values)
                st.success("Uspešno sačuvano!")
                st.rerun()

        with tab_io:
            col1, col2 = st.columns(2)
            with col1:
                st.write("### 📥 Export")
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                st.download_button(f"Preuzmi {tabela_za_rad}.xlsx", output.getvalue(), f"{tabela_za_rad}.xlsx", use_container_width=True)
            
            with col2:
                st.write("### 📤 Import")
                uploaded_file = st.file_uploader("Otpremi Excel", type=["xlsx"])
                if uploaded_file:
                    df_new = pd.read_excel(uploaded_file, engine='openpyxl')
                    if st.button("🚀 PREGAZI TABELU NOVIM PODACIMA"):
                        with conn.cursor() as cursor:
                            cursor.execute(f"TRUNCATE TABLE `{tabela_za_rad}`")
                            cols = ", ".join([f"`{c}`" for c in df_new.columns])
                            placeholders = ", ".join(["%s"] * len(df_new.columns))
                            sql_ins = f"INSERT INTO `{tabela_za_rad}` ({cols}) VALUES ({placeholders})"
                            for _, row in df_new.iterrows():
                                cursor.execute(sql_ins, tuple(None if pd.isna(x) else x for x in row))
                        st.success("Baza uspešno osvežena!")
                        st.rerun()
    else:
        st.warning(f"Tabela {tabela_za_rad} je prazna.")

    conn.close()
except Exception as e:
    st.error(f"Sistemska greška: {e}")
