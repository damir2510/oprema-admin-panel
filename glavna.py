import streamlit as st

# 1. OSNOVNA KONFIGURACIJA (Mora biti na samom početku)
st.set_page_config(page_title="BV Web App", layout="centered", page_icon="🏢")

# 2. DEFINISANJE SVIH STRANICA IZ PAGES FOLDERA
# Svaki fajl mora imati tačnu putanju "pages/ime_fajla.py"
p_pocetna = st.Page("glavna.py", title="Početna", icon="🏠", default=True)
p_oprema = st.Page("pages/oprema.py", title="Oprema", icon="🔍")
p_mapa = st.Page("pages/mapa_opreme.py", title="Mapa opreme", icon="🗺️")
p_admin = st.Page("pages/oprema_admin.py", title="Admin Panel", icon="⚙️")

# 3. KONTROLA MENIJA (NAVIGACIJA)
# Ovde ubacujemo SAMO one koje želimo da korisnik vidi u sidebaru
pg = st.navigation({
    "Glavni meni": [p_pocetna, p_oprema],
    # Mapa i Admin su izostavljeni odavde, pa su "skriveni" iz sidebara
})

# Pokretanje navigacije
pg.run()

# --- SADRŽAJ POČETNE STRANE (Pojavljuje se samo na Početnoj) ---
# Proveravamo da li je trenutna strana Početna da ne bi duplirali sadržaj na ostalim stranama
if st.navigation != p_pocetna:
    st.title("👋 Dobrodošli u BV Web App")
    st.markdown("---")

    st.subheader("Izaberite sekciju kojoj želite da pristupite:")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.success("🔍 **Sektor Opreme**")
        st.write("Pregled instrumenata, statusa i baždarenja.")
        # switch_page sada koristi objekat p_oprema definisan iznad
        if st.button("Uđi u evidenciju opreme", use_container_width=True):
            st.switch_page(p_oprema)

    st.markdown("---")
    with st.expander("📌 Aktuelno"):
        st.write("- Sistem za opremu je povezan sa Aiven SQL bazom.")
        st.write("- Radni sati su privremeno isključeni radi održavanja.")
