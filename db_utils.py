import pymysql
import pandas as pd
import streamlit as st

def get_conn():
    """Pravi konekciju sa Aiven MySQL bazom."""
    return pymysql.connect(
        host="mysql-22f7bcfd-nogalod-c393.d.aivencloud.com",
        user="avnadmin",
        password="AVNS_0qoNdSQVUuF9wTfHN8D",
        port=27698,
        database="defaultdb",
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'}
    )

def run_query(query, params=None):
    """Izvršava upit i vraća Pandas DataFrame."""
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchall()
            return pd.DataFrame(result) if result else pd.DataFrame()
    except Exception as e:
        st.error(f"Greška sa bazom: {e}")
        return pd.DataFrame()
    finally:
        if 'conn' in locals(): conn.close()
