import streamlit as st
import pandas as pd
import pymysql
import io

# 1. CSS ZA FORSIRANJE ŠIRINE (Popravljen parametar)
st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    div[data-testid="stDataFrame"] {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

st.title("🛠 Admin Panel")

tabela_za_rad = st.selectbox("Izaberi tabelu za uređivanje:", 
                            ["oprema", "istorija_servisa", "istorija_etaloniranja", "istorija_bazdarenja", "kulture_opsezi"])

try:
    conn = get_conn()
    df = pd.read_sql(f"SELECT * FROM `{tabela_za_rad}`", conn)
    conn.close()
    
    if not df.empty:
        # Čišćenje naziva kolona
        df.columns = [c.strip() for c in df.columns]

        tab_edit, tab_import = st.tabs(["📝 Brza Izmena", "📥 Import/Export"])

        with tab_edit:
            st.subheader(f"Uređivanje: {tabela_za_rad}")
            
            # EDITOR (Sada bi trebalo da vidiš podatke)
            edited_df = st.data_editor(
                df,
                use_container_width=True, 
                hide_index=True,
                num_rows="dynamic",
                column_config={"id": None},
                key=f"editor_{tabela_za_rad}",
                height=600
            )

            if st.button("💾 SAČUVAJ SVE IZMENE", type="primary"):
                kolone = [c for c in edited_df.columns if c != 'id']
                set_clause = ", ".join([f"`{c}`=%s" for c in kolone])
                sql = f"UPDATE `{tabela_za_rad}` SET {set_clause} WHERE id=%s"
                
                try:
                    conn = get_conn()
                    with conn.cursor() as cursor:
                        for _, row in edited_df.iterrows():
                            # Rešavanje NaN vrednosti za bazu
                            values = [None if pd.isna(row[c]) else row[c] for c in kolone] + [row['id']]
                            cursor.execute(sql, values)
                    st.success(f"Uspešno sačuvano!")
                    st.rerun()
                except Exception as e_up:
                    st.error(f"Greška: {e_up}")
                finally:
                    conn.close()

        with tab_import:
            c1, c2 = st.columns(2)
            with c1:
                st.write("### 📥 Export")
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                st.download_button(f"Preuzmi {tabela_za_rad}.xlsx", output.getvalue(), f"{tabela_za_rad}.xlsx", use_container_width=True)
            
            with c2:
                st.write("### 📤 Import")
                uploaded_file = st.file_uploader("Otpremi Excel (xlsx)", type=["xlsx"])
                if uploaded_file:
                    df_new = pd.read_excel(uploaded_file, engine='openpyxl')
                    if st.button("🚀 PREGAZI BAZU"):
                        try:
                            conn = get_conn()
                            with conn.cursor() as cursor:
                                cursor.execute(f"TRUNCATE TABLE `{tabela_za_rad}`")
                                cols = ", ".join([f"`{c}`" for c in df_new.columns])
                                placeholders = ", ".join(["%s"] * len(df_new.columns))
                                sql_ins = f"INSERT INTO `{tabela_za_rad}` ({cols}) VALUES ({placeholders})"
                                for _, row in df_new.iterrows():
                                    cursor.execute(sql_ins, tuple(None if pd.isna(x) else x for x in row))
                            st.success("Baza je osvežena!")
                            st.rerun()
                        except Exception as e_im:
                            st.error(f"Greška: {e_im}")
                        finally:
                            conn.close()
    else:
        st.warning("Tabela je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
