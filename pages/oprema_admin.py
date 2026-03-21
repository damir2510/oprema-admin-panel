import streamlit as st
import pandas as pd
import pymysql
import io

# --- NAVIGACIJA ---
st.sidebar.header("🚀 Navigacija")
if st.sidebar.button("📋 Pregled Opreme", use_container_width=True):
    st.switch_page("pages/oprema.py")
if st.sidebar.button("📍 Mapa opreme", use_container_width=True):
    st.switch_page("pages/mapa_opreme.py")

# --- KONEKCIJA ---
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698, database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'},
        autocommit=True
    )

st.title("🛠 Admin Panel - Univerzalni Upravnik")

# IZBOR TABELE KOJOM SE UPRAVLJA
tabela_za_rad = st.selectbox("Izaberi tabelu za uređivanje:",
                            ["oprema", "istorija_servisa", "istorija_etaloniranja", "istorija_bazdarenja", "kulture_opsezi"])

try:
    conn = get_conn()
    # Dinamički povlačimo izabranu tabelu
    df_raw = pd.read_sql(f"SELECT * FROM {tabela_za_rad}", conn)
    conn.close()

    if not df_raw.empty:
        # ČIŠĆENJE: Brisanje duplih headera ako postoje u bazi
        df = df_raw.copy()
        # Ako je prvi red isti kao naslov kolone, obriši ga
        for col in df.columns:
            df = df[df[col].astype(str).str.lower() != str(col).lower()]

        tab_edit, tab_import = st.tabs(["📝 Brza Izmena", "📥 Import/Export"])

        with tab_edit:
            st.subheader(f"Uređivanje tabele: {tabela_za_rad}")
            # Editor koji omogućava izmenu bilo kog polja
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={"id": None}, # Sakrivamo ID
                key=f"editor_{tabela_za_rad}"
            )

            if st.button("💾 SAČUVAJ IZMENE U BAZU", type="primary"):
                # AUTOMATSKO GENERISANJE SQL-a za bilo koju tabelu
                kolone = [c for c in edited_df.columns if c != 'id']
                set_clause = ", ".join([f"{c}=%s" for c in kolone])
                sql = f"UPDATE {tabela_za_rad} SET {set_clause} WHERE id=%s"

                try:
                    conn = get_conn()
                    with conn.cursor() as cursor:
                        for _, row in edited_df.iterrows():
                            # Priprema vrednosti za SQL
                            values = [row[c] for c in kolone] + [row['id']]
                            cursor.execute(sql, values)
                    conn.close()
                    st.success(f"Tabela {tabela_za_rad} je uspešno ažurirana!")
                    st.rerun()
                except Exception as e_up:
                    st.error(f"Greška pri čuvanju: {e_up}")

        with tab_import:
            st.subheader(f"Export/Import za {tabela_za_rad}")

            # --- EXPORT SVEGA ---
            st.write("1. Preuzmi trenutne podatke:")
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            st.download_button(f"📥 Preuzmi {tabela_za_rad}.xlsx", output.getvalue(), f"{tabela_za_rad}.xlsx")

            st.divider()

            # --- IMPORT SVEGA ---
            st.write("2. Masovni uvoz (Pregazi/Dodaj):")
            uploaded_file = st.file_uploader("Otpremi Excel", type=["xlsx"])
            if uploaded_file:
                df_upload = pd.read_excel(uploaded_file, engine='openpyxl')
                st.write("Pregled fajla:")
                st.dataframe(df_upload.head(5))

                if st.button("🚀 POKRENI MASOVNI UVOZ"):
                    # Logika: Brisanje stare i upis nove (najbrži način za kompletan uvoz)
                    try:
                        conn = get_conn()
                        with conn.cursor() as cursor:
                            # Opciono: cursor.execute(f"DELETE FROM {tabela_za_rad}")
                            for _, row in df_upload.iterrows():
                                cols = ", ".join(df_upload.columns)
                                placeholder = ", ".join(["%s"] * len(df_upload.columns))
                                sql_ins = f"INSERT INTO {tabela_za_rad} ({cols}) VALUES ({placeholder})"
                                cursor.execute(sql_ins, tuple(row))
                        conn.close()
                        st.success("Uspešan uvoz!")
                    except Exception as e_im:
                        st.error(f"Greška pri uvozu: {e_im}")
    else:
        st.info(f"Tabela {tabela_za_rad} je prazna.")

except Exception as e:
    st.error(f"Sistemska greška: {e}")
