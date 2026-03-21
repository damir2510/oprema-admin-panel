import streamlit as st
import pandas as pd
import pymysql
import io

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

# 2. STRUKTURA TABELE
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

# 3. EXCEL IZVOZ
def export_to_excel_clean(df, sheet_name):
    output = io.BytesIO()
    cols_to_hide = ['oprema_id', 'id_opreme']
    df_export = df.drop(columns=[c for c in cols_to_hide if c in df.columns])
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
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

    t1, t2, t3 = st.tabs(["📝 Direktan unos & Pretraga", "📥 Excel Alati", "🗑️ Brisanje"])

    # --- TAB 1: DIREKTAN UNOS + FILTERI ---
    with t1:
        df_all = get_table_structure(izabrana_tabela)
        
        # --- SEKCIJA ZA FILTERE ---
        st.info("💡 Koristi filtere ispod da brzo nađeš aparat. Tabela se automatski osvežava.")
        col_f1, col_f2 = st.columns([1, 2])
        
        with col_f1:
            sektori = ["SVI"]
            if 'sektor' in df_all.columns:
                sektori += sorted(df_all['sektor'].unique().tolist())
            izabrani_sektor = st.selectbox("📍 Filtriraj po sektoru:", sektori)
            
        with col_f2:
            search_query = st.text_input("🔍 Pretraži (Inv. broj, Naziv, Proizvođač...):", "").lower()

        # Primena filtera
        df_filtered = df_all.copy()
        if izabrani_sektor != "SVI" and 'sektor' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['sektor'] == izabrani_sektor]
            
        if search_query:
            mask = df_filtered.astype(str).apply(lambda x: x.str.lower().str.contains(search_query)).any(axis=1)
            df_filtered = df_filtered[mask]

        # PRIKAZ TABELE
        st.write(f"Pronađeno stavki: **{len(df_filtered)}**")
        edited_df = st.data_editor(
            df_filtered, 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, 
            key=f"editor_{izabrana_tabela}"
        )
        
        if st.button("💾 SAČUVAJ IZMENE U BAZU"):
            conn = get_conn()
            cur = conn.cursor()
            try:
                for idx, row in edited_df.iterrows():
                    sql_cols = [c for c in edited_df.columns if c != 'id']
                    
                    # Auto FK povezivanje preko inventarnog broja
                    if izabrana_tabela != "oprema" and "inventarni_broj" in row:
                        inv = str(row['inventarni_broj']).strip()
                        cur.execute("SELECT id FROM oprema WHERE inventarni_broj = %s", (inv,))
                        res = cur.fetchone()
                        fk_name = "oprema_id" if "oprema_id" in sql_cols else ("id_opreme" if "id_opreme" in sql_cols else None)
                        if fk_name and res: row[fk_name] = res['id']
                    
                    vals = [None if pd.isna(row[c]) or str(row[c]) in ['-', 'nan', 'None'] else row[c] for c in sql_cols]
                    
                    if not pd.isna(row.get('id')) and str(row.get('id')) != '':
                        cur.execute(f"UPDATE {izabrana_tabela} SET {', '.join([f'{c}=%s' for c in sql_cols])} WHERE id=%s", vals + [int(row['id'])])
                    else:
                        cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(sql_cols)}) VALUES ({', '.join(['%s']*len(sql_cols))})", vals)
                
                conn.commit()
                st.success("Baza uspešno ažurirana!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Greška: {e}")
            finally:
                conn.close()

    # --- TAB 2: EXCEL UVOZ/IZVOZ ---
    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 📤 Izvoz cele tabele")
            df_exp = get_table_structure(izabrana_tabela)
            st.download_button(
                label=f"Preuzmi {izabrana_tabela}.xlsx",
                data=export_to_excel_clean(df_exp, izabrana_tabela),
                file_name=f"{izabrana_tabela}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with c2:
            st.write("### 📥 Uvoz iz Excela")
            up_file = st.file_uploader("Otpremite Excel", type=['xlsx'])
            if up_file:
                df_u = pd.read_excel(up_file, engine='openpyxl').fillna('-')
                if st.button("🚀 POKRENI SINHRONIZACIJU"):
                    conn = get_conn(); cur = conn.cursor()
                    try:
                        cur.execute(f"DESCRIBE {izabrana_tabela}"); sql_cols = [r['Field'] for r in cur.fetchall()]
                        n, u = 0, 0
                        for _, row in df_u.iterrows():
                            data = {}
                            for c in sql_cols:
                                if c == 'id': continue
                                if c in df_u.columns: data[c] = None if str(row[c]) in ['-', 'nan'] else row[c]
                            
                            cols, vals = list(data.keys()), list(data.values())
                            row_id = row.get('id')
                            if not pd.isna(row_id) and str(row_id) not in ['-', 'nan']:
                                cur.execute(f"UPDATE {izabrana_tabela} SET {', '.join([f'{c}=%s' for c in cols])} WHERE id=%s", vals + [int(row_id)])
                                u += 1
                            else:
                                cur.execute(f"INSERT INTO {izabrana_tabela} ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(cols))})", vals)
                                n += 1
                        conn.commit(); st.success(f"Dodato: {n}, Izmenjeno: {u}"); st.cache_data.clear()
                    except Exception as e: st.error(f"Greška: {e}")
                    finally: conn.close()

    # --- TAB 3: BRISANJE ---
    with t3:
        ident = "inventarni_broj" if izabrana_tabela == "oprema" else "id"
        val_del = st.text_input(f"Unesi {ident} za brisanje:")
        if st.button("❌ OBRIŠI IZ BAZE"):
            if val_del:
                conn = get_conn(); cur = conn.cursor()
                cur.execute(f"DELETE FROM {izabrana_tabela} WHERE {ident} = %s", (val_del,))
                conn.commit(); conn.close(); st.warning("Obrisano."); st.rerun()
else:
    st.info("Unesite lozinku u bočnom meniju.")
