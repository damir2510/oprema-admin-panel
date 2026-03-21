import streamlit as st
import pandas as pd
import pymysql
import io
from datetime import datetime

# 1. KONEKCIJA SA BAZOM
def get_conn():
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin", 
        password="AVNS_0qoNdSQVUuF9wTfHN8D", 
        port=27698, 
        database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'}
    )

# 2. STRUKTURA TABELE (Čak i ako je prazna)
def get_table_structure(tabela):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {tabela}")
            rows = cur.fetchall()
            cur.execute(f"DESCRIBE {tabela}")
            cols = [r['Field'] for r in cur.fetchall()]
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)
    finally:
        conn.close()

# 3. EXCEL IZVOZ (Formatiranje i zaštita)
def export_to_excel_clean(df, sheet_name):
    output = io.BytesIO()
    # Sakrivamo sistemske ključeve da ne zbunjuju korisnika
    cols_to_hide = ['oprema_id', 'id_opreme']
    df_export = df.drop(columns=[c for c in cols_to_hide if c in df.columns])
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Stilovi
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        l_fmt = workbook.add_format({'bg_color': '#F2F2F2', 'locked': True, 'border': 1})
        u_fmt = workbook.add_format({'locked': False, 'border': 1})
        
        worksheet.protect() 
        for i, col in enumerate(df_export.columns):
            worksheet.write(0, i, col, h_fmt)
            width = max(df_export[col].astype(str).map(len).max() if not df_export.empty else 10, len(col)) + 2
            fmt = l_fmt if col.lower() == 'id' else u_fmt
            worksheet.set_column(i, i, width, fmt)
            
    return output.getvalue()

st.set_page_config(page_title="Master Admin Panel", layout="wide")

# --- LOGIN PROVERA ---
if st.sidebar.text_input("🔐 Lozinka:", type="password") == "damir123":
    st.title("⚙️ Master Admin Panel")
    
    sve_tabele = ["oprema", "istorija_bazdarenja", "kulture_opsezi", "istorija_servisa", "istorija_etaloniranja", "istorija_provera"]
    izabrana_tabela = st.selectbox("Izaberi tabelu za rad:", sve_tabele, key="main_sel")

    t1, t2, t3 = st.tabs(["📝 Direktan unos", "📥 Excel Alati", "🗑️ Brisanje"])

    # --- TAB 1: DIREKTAN UNOS ---
    with t1:
        df_current = get_table_structure(izabrana_tabela)
        edited_df = st.data_editor(df_current, num_rows="dynamic", use_container_width=True, hide_index=True, key="editor_key")
        
        if st.button("💾 SAČUVAJ IZMENE IZ TABELE"):
            conn = get_conn()
            cur = conn.cursor()
            try:
                for idx, row in edited_df.iterrows():
                    sql_cols = [c for c in edited_df.columns if c != 'id']
                    
                    # Automatsko povezivanje Foreign Key-a preko inventarnog broja
                    if izabrana_tabela != "oprema" and "inventarni_broj" in row:
                        inv = str(row['inventarni_broj']).strip()
                        cur.execute("SELECT id FROM oprema WHERE inventarni_broj = %s", (inv,))
                        res = cur.fetchone()
                        fk_name = "oprema_id" if "oprema_id" in sql_cols else ("id_opreme" if "id_opreme" in sql_cols else None)
                        if fk_name and res: row[fk_name] = res['id']
                    
                    vals = [None if pd.isna(row[c]) or str(row[c]) in ['-', 'nan', 'None'] else row[c] for c in sql_cols]
                    
                    if not pd.isna(row.get('id')) and str(row.get('id')) != '':
                        # UPDATE postojeći red
                        cur.execute(f"UPDATE {izabrana_tabela} SET {', '.join([f'{c}=%s' for c in sql_cols])} WHERE id=%s", vals + [int(row['id'])])
                    else:
                        # INSERT novi red
                        cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(sql_cols)}) VALUES ({', '.join(['%s']*len(sql_cols))})", vals)
                
                conn.commit()
                st.success("Baza uspešno ažurirana!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Greška prilikom čuvanja: {e}")
            finally:
                conn.close()

    # --- TAB 2: EXCEL UVOZ/IZVOZ ---
    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 📤 Izvoz")
            df_exp = get_table_structure(izabrana_tabela)
            excel_data = export_to_excel_clean(df_exp, izabrana_tabela)
            
            st.download_button(
                label=f"Preuzmi {izabrana_tabela}.xlsx",
                data=excel_data,
                file_name=f"{izabrana_tabela}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with c2:
            st.write("### 📥 Uvoz")
            up_file = st.file_uploader("Otpremite Excel fajl", type=['xlsx'], key="excel_up")
            if up_file:
                # Koristimo openpyxl za čitanje (mora biti u requirements.txt)
                df_u = pd.read_excel(up_file, engine='openpyxl').fillna('-')
                df_u.columns = [c.strip().lower() for c in df_u.columns]
                
                if st.button("🚀 SINHRONIZUJ IZ EXCELA"):
                    conn = get_conn()
                    cur = conn.cursor()
                    try:
                        cur.execute(f"DESCRIBE {izabrana_tabela}")
                        sql_cols = [r['Field'] for r in cur.fetchall()]
                        n, u = 0, 0
                        
                        for idx, row in df_u.iterrows():
                            data = {}
                            inv = str(row.get('inventarni_broj', '')).strip()
                            fk_name = "oprema_id" if "oprema_id" in sql_cols else ("id_opreme" if "id_opreme" in sql_cols else None)
                            
                            if fk_name and inv != '-':
                                cur.execute("SELECT id FROM oprema WHERE inventarni_broj = %s", (inv,))
                                res = cur.fetchone()
                                if res: data[fk_name] = res['id']
                            
                            for c in sql_cols:
                                if c == 'id' or c == fk_name: continue
                                if c in df_u.columns:
                                    val = row[c]
                                    if pd.isna(val) or str(val) in ['-', 'nan', 'None']:
                                        data[c] = None
                                    elif 'datum' in c or 'vazi' in c:
                                        try: data[c] = pd.to_datetime(val).strftime('%Y-%m-%d')
                                        except: data[c] = None
                                    else:
                                        data[c] = val
                            
                            cols, vals = list(data.keys()), list(data.values())
                            row_id = row.get('id')
                            
                            if not pd.isna(row_id) and str(row_id) not in ['-', 'nan']:
                                cur.execute(f"UPDATE {izabrana_tabela} SET {', '.join([f'{c}=%s' for c in cols])} WHERE id=%s", vals + [int(row_id)])
                                u += 1
                            else:
                                if cols:
                                    cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))})", vals)
                                    n += 1
                        
                        conn.commit()
                        st.success(f"Sinhronizacija završena! Dodato: {n}, Izmenjeno: {u}")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Greška kod uvoza: {e}")
                    finally:
                        conn.close()

    # --- TAB 3: BRISANJE ---
    with t3:
        st.subheader("🗑️ Brisanje podataka")
        ident = "inventarni_broj" if izabrana_tabela == "oprema" else "id"
        val_del = st.text_input(f"Unesi {ident} za brisanje:", key="del_input")
        
        if st.button("❌ TRAJNO OBRIŠI"):
            if val_del:
                conn = get_conn()
                cur = conn.cursor()
                try:
                    cur.execute(f"DELETE FROM {izabrana_tabela} WHERE {ident} = %s", (val_del,))
                    conn.commit()
                    st.warning(f"Podatak sa {ident} = {val_del} je obrisan.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Greška: {e}")
                finally:
                    conn.close()
            else:
                st.error("Polje ne sme biti prazno!")
else:
    st.info("Prijavite se lozinkom za pristup admin panelu.")
