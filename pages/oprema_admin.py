import streamlit as st
import pandas as pd
import pymysql
import io

# --- 1. KONEKCIJA ---
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

# 2. IZBOR TABELE
tabela_za_rad = st.selectbox("Izaberi tabelu za rad:", 
                            ["oprema", "istorija_servisa", "istorija_etaloniranja", "istorija_bazdarenja", "kulture_opsezi"])

try:
    conn = get_conn()
    # Čitanje sirovih podataka iz izabrane tabele
    df_raw = pd.read_sql(f"SELECT * FROM `{tabela_za_rad}`", conn)
    conn.close()
    
    if not df_raw.empty:
        # --- ČIŠĆENJE PODATAKA (Osigurava da nema praznih redova u prikazu) ---
        df = df_raw.copy()
        df = df.astype(object).replace([None, 'None', 'nan', 'NaN', 'NaT'], '')
        df.columns = [str(c).strip() for c in df.columns]

        tab_edit, tab_io = st.tabs(["📝 Brza Izmena", "📥 Import/Export"])

        with tab_edit:
            st.subheader(f"Uređivanje: {tabela_za_rad}")
            
            # DATA EDITOR - Maksimalna širina
            edited_df = st.data_editor(
                df,
                use_container_width=True, 
                hide_index=True,
                num_rows="dynamic",
                column_config={"id": None}, # ID nevidljiv, ali prisutan
                key=f"editor_{tabela_za_rad}",
                height=600
            )

            if st.button("💾 SAČUVAJ SVE IZMENE", type="primary", use_container_width=True):
                try:
                    conn = get_conn()
                    with conn.cursor() as cursor:
                        # Dinamički UPDATE za bilo koju tabelu i bilo koji broj kolona
                        kolone = [c for c in edited_df.columns if c != 'id']
                        set_clause = ", ".join([f"`{c}`=%s" for c in kolone])
                        sql = f"UPDATE `{tabela_za_rad}` SET {set_clause} WHERE id=%s"
                        
                        for _, row in edited_df.iterrows():
                            # Vraćanje praznih polja u NULL za SQL
                            values = [None if str(row[c]).strip() == "" else row[c] for c in kolone] + [row['id']]
                            cursor.execute(sql, values)
                    
                    st.success(f"Tabela '{tabela_za_rad}' je uspešno ažurirana!")
                    st.rerun()
                except Exception as e_up:
                    st.error(f"Greška pri upisu: {e_up}")
                finally:
                    conn.close()

        with tab_io:
            col1, col2 = st.columns(2)
            with col1:
                st.write("### 📥 Export")
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                st.download_button(f"Preuzmi {tabela_za_rad}.xlsx", output.getvalue(), f"{tabela_za_rad}.xlsx", use_container_width=True)
            
            with col2:
                st.write("### 📤 Import")
                uploaded_file = st.file_uploader("Otpremi Excel (xlsx)", type=["xlsx"])
                if uploaded_file:
                    df_new = pd.read_excel(uploaded_file, engine='openpyxl')
                    if st.button("🚀 PREGAZI TABELU NOVIM PODACIMA", use_container_width=True):
                        try:
                            conn = get_conn()
                            with conn.cursor() as cursor:
                                cursor.execute(f"TRUNCATE TABLE `{tabela_za_rad}`")
                                cols = ", ".join([f"`{c}`" for c in df_new.columns])
                                placeholders = ", ".join(["%s"] * len(df_new.columns))
                                sql_ins = f"INSERT INTO `{tabela_za_rad}` ({cols}) VALUES ({placeholders})"
                                for _, row in df_new.iterrows():
                                    cursor.execute(sql_ins, tuple(None if pd.isna(x) else x for x in row))
                            st.success("Baza je uspešno osvežena!")
                            st.rerun()
                        except Exception as e_im:
                            st.error(f"Greška pri uvozu: {e_im}")
                        finally:
                            conn.close()
    else:
        st.info(f"Tabela '{tabela_za_rad}' je trenutno prazna.")

except Exception as e:
    st.error(f"Greška pri učitavanju: {e}")
