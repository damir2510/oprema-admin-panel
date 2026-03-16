try:
    conn = get_conn()
    # 1. Vučemo sve podatke iz baze
    df = pd.read_sql("SELECT * FROM oprema", conn)
    conn.close()

    if not df.empty:
        # 2. Sređivanje naziva kolona (uklanjamo razmake i mala slova)
        df.columns = [c.strip().lower() for c in df.columns]

        # 3. ČIŠĆENJE SMEĆA: Izbacujemo redove gde je inventarni_broj isti kao naziv kolone
        # Proveravamo da li kolona postoji pre nego što je filtriramo
        if 'inventarni_broj' in df.columns:
            df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni_broj']
            df = df[df['inventarni_broj'].astype(str).str.lower() != 'inventarni broj']
        
        # Dodatno čišćenje: izbaci potpuno prazne redove ako ih ima
        df = df.dropna(how='all')

        # 4. Pretraga
        search = st.text_input("🔍 Pretraži (po nazivu, bar-kodu, radniku...):", "")
        
        if search:
            mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)
            df_prikaz = df[mask]
        else:
            df_prikaz = df

        # 5. Prikaz tabele
        st.dataframe(
            df_prikaz, 
            use_container_width=True, 
            hide_index=True
        )

        st.success(f"Pronađeno realnih aparata: {len(df_prikaz)}")
        
    else:
        st.warning("Tabela je prazna.")

except Exception as e:
    st.error(f"Greška: {e}")
