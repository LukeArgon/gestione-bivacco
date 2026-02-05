import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Prenotazioni Bivacco", page_icon="⛺", layout="wide")

# PASSWORD
PASSWORD_EVENTO = "vara26" 
PASSWORD_STAFF = "coca"

# TOTALE LETTI
POSTI_LETTO_TOTALI = 70

# LISTE GRUPPI
GRUPPI = {
    "Luna d'Argento": ["Bimbo A", "Bimbo B", "Bimbo C"], 
    "Mario Re": ["Bimbo D", "Bimbo E"],
    "Reparto": ["Marco", "Giulia", "Luca"],
    "Noviziato": ["Andrea", "Chiara"],
    "Clan": ["Rover 1", "Scolta 2"]
}

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == PASSWORD_EVENTO:
        st.session_state.authenticated = True
    else:
        st.error("Password errata.")

if not st.session_state.authenticated:
    st.title("🔒 Area Riservata")
    st.text_input("Inserisci la password dell'evento:", type="password", key="password_input", on_change=check_password)
    st.stop()

# --- 3. CONNESSIONE GOOGLE SHEETS ---
@st.cache_resource(ttl=0)
def connect_to_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(st.secrets["private_url"]).sheet1
    return sheet

try:
    sheet = connect_to_sheet()
except Exception as e:
    st.error(f"Errore di connessione: {e}")
    st.stop()

def get_data():
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty and "Numero Persone" in df.columns:
        df["Numero Persone"] = pd.to_numeric(df["Numero Persone"], errors='coerce').fillna(0)
    return df

# --- 4. INTERFACCIA ---
menu = st.sidebar.radio("Menu", ["📝 Prenotazione", "🔐 Area Staff"])

if menu == "📝 Prenotazione":
    # TITOLI E POSIZIONE
    st.title("⛺ Prenotazione bivacco di gruppo")
    st.subheader("9/10 maggio 2026 - Base scout il Rostiolo, Vara")
    
    st.markdown("[📍 Vedi posizione su Google Maps](https://maps.app.goo.gl/df3NHq2cC9QfrESk7)")
    
    st.markdown("---")
    
    # --- CALCOLO POSTI RIMASTI ---
    df = get_data()
    posti_occupati = 0
    if not df.empty and "Sistemazione" in df.columns:
        posti_occupati = df[df["Sistemazione"] == "Letto"]["Numero Persone"].sum()
    
    rimasti = POSTI_LETTO_TOTALI - posti_occupati
    if rimasti < 0: rimasti = 0

    # VISUALIZZAZIONE A DESTRA
    col_spacer, col_tot, col_disp = st.columns([6, 2, 2]) 
    
    with col_tot:
        st.metric("Totale Letti", POSTI_LETTO_TOTALI)
    with col_disp:
        st.metric("Letti Disponibili", int(rimasti))
    
    st.markdown("---")

    # --- SCHEDE SEPARATE (TAB) ---
    tab1, tab2 = st.tabs(["👪 Sono un Genitore", "⚜️ Sono Capo/Ex-scout/Amico"])

    # Funzione salvataggio unica
    def salva_prenotazione(gruppo, nome_rif, numero, giorno, tipo_sis):
        if not nome_rif:
            st.error("⚠️ Inserisci il nome di riferimento!")
            return
        
        # LOGICA DOMENICA
        # Se hanno messo Domenica, forziamo la sistemazione a "Nessuna" anche se hanno cliccato altro
        msg_extra = ""
        if giorno == "Domenica":
            tipo_sis = "Nessuna (Solo Domenica)"
            msg_extra = "🔴 Nota: Hai selezionato 'Domenica', quindi non è stato scalato nessun posto letto."
        
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            gruppo,
            nome_rif,
            numero,
            giorno,
            tipo_sis
        ]
        sheet.append_row(row)
        
        if msg_extra:
            st.error(msg_extra) # Messaggio popup rosso
            
        st.success("✅ CONFERMA: La tua prenotazione è stata salvata correttamente!")
        st.balloons()
        time.sleep(3)
        st.rerun()

    # --- TAB 1: GENITORI ---
    with tab1:
        with st.form("form_genitori"):
            st.write("### Prenotazione Famiglie")
            gruppo_scelto = st.selectbox("Gruppo del ragazzo/a", list(GRUPPI.keys()))
            
            riferimento = ""
            if gruppo_scelto:
                riferimento = st.selectbox("Nome del ragazzo/a", GRUPPI[gruppo_scelto])
            
            num_persone = st.number_input("Numero totale persone", min_value=1, value=1, key="n_fam")
            
            c1, c2 = st.columns(2)
            arrivo = c1.radio("Arrivo", ["Sabato", "Domenica"], horizontal=True, key="arr_fam")
            
            # --- SEZIONE SISTEMAZIONE ---
            st.markdown("---")
            # MESSAGGIO CORRETTO
            st.markdown(":red[**Se arrivi Domenica, la scelta qui sotto non consumerà posti letto (verrai segnato presente per la giornata).**]")
            
            opts = ["Tenda"]
            if rimasti >= num_persone: opts.insert(0, "Letto")
            else: st.warning(f"Rimasti solo {int(rimasti)} letti. Scegliete Tenda.")
            
            sistemazione = c2.radio("Sistemazione Preferita", opts, key="sis_fam")

            if st.form_submit_button("Conferma Prenotazione"):
                salva_prenotazione(gruppo_scelto, riferimento, num_persone, arrivo, sistemazione)

    # --- TAB 2: CAPI / EX SCOUT / AMICI ---
    with tab2:
        with st.form("form_esterni"):
            st.write("### Prenotazione Capi, Amici & Ex Scout")
            nome_manuale = st.text_input("Nome e Cognome")
            
            num_persone_ex = st.number_input("Numero totale persone", min_value=1, value=1, key="n_ex")
            
            c1, c2 = st.columns(2)
            arrivo_ex = c1.radio("Arrivo", ["Sabato", "Domenica"], horizontal=True, key="arr_ex")
            
            # --- SEZIONE SISTEMAZIONE ---
            st.markdown("---")
            # MESSAGGIO CORRETTO
            st.markdown(":red[**Se arrivi Domenica, la scelta qui sotto non consumerà posti letto (verrai segnato presente per la giornata).**]")

            opts_ex = ["Tenda"]
            if rimasti >= num_persone_ex: opts_ex.insert(0, "Letto")
            else: st.warning(f"Rimasti solo {int(rimasti)} letti. Scegliete Tenda.")
            
            sistemazione_ex = c2.radio("Sistemazione Preferita", opts_ex, key="sis_ex")
            
            if st.form_submit_button("Conferma Prenotazione"):
                salva_prenotazione("Capo/Ex-Scout/Amico", nome_manuale, num_persone_ex, arrivo_ex, sistemazione_ex)

elif menu == "🔐 Area Staff":
    st.title("Admin - Elenco Iscritti")
    pwd = st.sidebar.text_input("Password Staff", type="password")
    
    if pwd == PASSWORD_STAFF:
        df = get_data()
        if not df.empty:
            st.dataframe(df)
            
            # Statistiche rapide
            tot_persone = df['Numero Persone'].sum()
            tot_letti = df[df["Sistemazione"] == "Letto"]["Numero Persone"].sum()
            st.success(f"Totale presenze: {tot_persone} | Di cui in Letto: {tot_letti}")
    else:
        st.warning("Inserisci password staff.")
