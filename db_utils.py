import pymysql
import pandas as pd
import streamlit as st
import os

def get_conn():
    """
    Pravi konekciju sa Aiven MySQL bazom.
    Prvo pokušava da povuče podatke iz sistemskih promenljivih (Railway/Render),
    a ako ih nema, koristi tvoje upisane podatke.
    """
    return pymysql.connect(
        host=os.getenv("DB_HOST", "mysql-22f7bcfd-nogalod-c393.d.aivencloud.com"),
        user=os.getenv("DB_USER", "avnadmin"),
        password=os.getenv("DB_PASS", "AVNS_0qoNdSQVUuF9wTfHN8D"),
        port=int(os.getenv("DB_PORT", 27698)),
        database=os.getenv("DB_NAME", "defaultdb"),
        cursorclass=pymysql.cursors.DictCursor,
        ssl={'ssl-mode': 'REQUIRED'}
    )

def run_query(query, params=None):
    """
    Izvršava SQL upit i vraća Pandas DataFrame.
    Automatski zatvara konekciju nakon izvršavanja.
    """
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchall()
            # Vraća DataFrame ili prazan DataFrame ako nema rezultata
            return pd.DataFrame(result) if result else pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Greška sa bazom podataka: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def execute_db(query, params=None):
    """
    Pomoćna funkcija za INSERT, UPDATE i DELETE operacije
    koje ne vraćaju tabelu već samo menjaju podatke.
    """
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ SQL Greška (izvršavanje): {e}")
        return False
    finally:
        if conn:
            conn.close()
