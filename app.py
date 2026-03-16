# --- OVDE POČINJU TABOVI UNUTAR MATIČNOG KARTONA (ZAMENI DONJI DEO KODA) ---

if izabrani_broj:
    rezultat = df[df['inventarni_broj'].astype(str) == str(izabrani_broj)]

    if not rezultat.empty:
        instrument = rezultat.iloc[0]
        model_instrumenta = str(instrument.get('naziv_proizvodjac', '')).strip()
        inv_broj_str = str(izabrani_broj)

        st.markdown(f"### Instrument br: <span style='color:#ff4b4b'>{izabrani_broj}</span>", unsafe_allow_html=True)
        
        # DEFINICIJA TABA
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Osnovni podaci", "🌾 Kulture i Opsezi", "🛠️ Servis i Provere", "📏 Etaloniranje"])

        # --- TAB 1: OSNOVNI PODACI (Tvoj prethodni karton) ---
        with tab1:
            polja = {
                "Vrsta opreme": "vrsta_opreme", "Proizvođač": "proizvodjac", "Naziv": "naziv_proizvodjac",
                "Serijski broj": "seriski_broj", "Datum baždarenja": "datum_bazdarenja", "Važi do": "vazi_do",
                "Radna temperatura": "radna_temperatura", "Relativna vlažnost": "rel_vlaznost",
                "Opseg merenja": "opseg_merenja", "Klasa tačnosti": "klasa_tacnosti", "Preciznost": "preciznost", "Podeok": "podeok"
            }
            popunjena_polja = [(l, instrument[c]) for l, c in polja.items() if c in instrument and pd.notna(instrument[c]) and str(instrument[c]).strip() not in ["", "-", "nan", "None", "0"]]
            
            if popunjena_polja:
                cols = st.columns(4)
                for i, (label, value) in enumerate(popunjena_polja):
                    with cols[i % 4]:
                        st.caption(label)
                        st.write(f"**{value}**")
            else:
                st.info("Nema unetih tehničkih karakteristika.")

        # --- TAB 2: KULTURE I OPSEZI (Povezivanje preko NAZIVA MODELA) ---
        with tab2:
            st.write(f"Traženje kultura za model: `{model_instrumenta}`")
            try:
                conn = get_conn()
                # Povezujemo preko kolone koja se u bazi verovatno zove 'naziv' ili 'model'
                # Prilagodi naziv kolone 'naziv_opreme' ako se u tabeli kulture_opsezi zove drugačije
                query_kulture = "SELECT kultura, min_opseg, max_opseg FROM kulture_opsezi WHERE naziv_opreme = %s"
                df_kulture = pd.read_sql(query_kulture, conn, params=(model_instrumenta,))
                conn.close()

                if not df_kulture.empty:
                    st.table(df_kulture) # Čist prikaz bez search-a
                else:
                    st.info(f"Nisu pronađeni definisani opsezi kultura za model {model_instrumenta}.")
            except Exception as e:
                st.error(f"Greška pri dohvatanju kultura: {e}")

        # --- TAB 3: SERVIS I PROVERE (Povezivanje preko INVENTARNOG BROJA) ---
        with tab3:
            try:
                conn = get_conn()
                # Ovde pretpostavljamo da tabele imaju kolonu 'inventarni_broj'
                query_servis = "SELECT datum_servisa, opis_kvara, uradjeno, radnik FROM istorija_servisa WHERE inventarni_broj = %s ORDER BY datum_servisa DESC"
                df_servis = pd.read_sql(query_servis, conn, params=(inv_broj_str,))
                
                query_provere = "SELECT datum_provere, rezultat, napomena FROM istorija_provera WHERE inventarni_broj = %s ORDER BY datum_provere DESC"
                df_provere = pd.read_sql(query_provere, conn, params=(inv_broj_str,))
                conn.close()

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.write("**Istorija servisa:**")
                    st.dataframe(df_servis, use_container_width=True, hide_index=True) if not df_servis.empty else st.write("Nema zabeleženih servisa.")
                with col_s2:
                    st.write("**Periodične provere:**")
                    st.dataframe(df_provere, use_container_width=True, hide_index=True) if not df_provere.empty else st.write("Nema zabeleženih provera.")
            except Exception as e:
                st.error(f"Greška pri dohvatanju servisa: {e}")

        # --- TAB 4: ETALONIRANJE (Povezivanje preko INVENTARNOG BROJA) ---
        with tab4:
            try:
                conn = get_conn()
                query_etalon = "SELECT datum_etaloniranja, broj_uverenja, laboratorija, vazi_do FROM istorija_etaloniranja WHERE inventarni_broj = %s ORDER BY datum_etaloniranja DESC"
                df_etalon = pd.read_sql(query_etalon, conn, params=(inv_broj_str,))
                conn.close()

                if not df_etalon.empty:
                    st.dataframe(df_etalon, use_container_width=True, hide_index=True)
                else:
                    st.info("Nema podataka o prethodnim etaloniranjima.")
            except Exception as e:
                st.error(f"Greška pri dohvatanju etaloniranja: {e}")

    else:
        st.warning(f"Instrument sa brojem {izabrani_broj} nije pronađen.")
