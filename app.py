import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="Prenotazioni Bivacco", page_icon="⛺", layout="wide")

# PASSWORD
PASSWORD_EVENTO = "fazzolettone2024" 
PASSWORD_STAFF = "capi123"

# POSTI LETTO TOTALI
POSTI_LETTO_TOTALI = 60

# LISTE GRUPPI (Senza Ex-Scout, che gestiremo a parte)
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
    st.title("🔒 Area Riservata Bivacco")
    st.text_input("Password evento:", type="password", key="password_input", on_change=check_password)
    st.stop()

# --- 3. CONNESSIONE GOOGLE SHEETS ---
# ttl=0 costringe l'app a rileggere il foglio ogni volta che si aggiorna
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
    # Scarica i dati e si assicura che il numero persone sia un numero
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty and "Numero Persone" in df.columns:
        df["Numero Persone"] = pd.to_numeric(df["Numero Persone"], errors='coerce').fillna(0)
    return df

# --- 4. INTERFACCIA ---
menu = st.sidebar.radio("Menu", ["📝 Prenotazione", "🔐 Area Staff"])

if menu == "📝 Prenotazione":
    st.title("⛺ Prenotazione Bivacco")
    
    # --- CALCOLO POSTI RIMASTI ---
    df = get_data()
    posti_occupati = 0
    
    if not df.empty and "Sistemazione" in df.columns:
        # Somma solo le persone che hanno "Letto"
        posti_occupati = df[df["Sistemazione"] == "Letto"]["Numero Persone"].sum()
    
    rimasti = POSTI_LETTO_TOTALI - posti_occupati
    if rimasti < 0: rimasti = 0 # Per sicurezza

    # Visualizzazione Contatore
    col1, col2 = st.columns(2)
    col1.metric("Totale Letti", POSTI_LETTO_TOTALI)
    col2.metric("Letti Disponibili", int(rimasti))
    st.markdown("---")

    # --- SCHEDE SEPARATE (TAB) ---
    tab1, tab2 = st.tabs(["👪 Sono un Genitore", "⚜️ Sono Ex-Scout / Amico"])

    # Funzione unica per salvare i dati
    def salva_prenotazione(gruppo, nome_rif, numero, giorno, tipo_sis):
        if not nome_rif:
            st.error("⚠️ Inserisci il nome di riferimento!")
            return
        
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"), # Data
            gruppo,       # Gruppo
            nome_rif,     # Riferimento
            numero,       # Numero Persone
            giorno,       # Arrivo
            tipo_sis      # Sistemazione
        ]
        sheet.append_row(row)
        st.success("✅ AVVENUTA PRENOTAZIONE! Grazie.")
        st.balloons()
        time.sleep(2) # Aspetta 2 secondi per far leggere il messaggio
        st.rerun()    # Ricarica la pagina

    # --- TAB 1: GENITORI ---
    with tab1:
        with st.form("form_genitori"):
            st.write("### Prenotazione Famiglie")
            gruppo_scelto = st.selectbox("Gruppo del ragazzo/a", list(GRUPPI.keys()))
            if gruppo_scelto:
                riferimento = st.selectbox("Nome del ragazzo/a", GRUPPI[gruppo_scelto])
            
            num_persone = st.number_input("Numero totale persone (incluso ragazzo)", min_value=1, value=1, key="n_fam")
            
            c1, c2 = st.columns(2)
            arrivo = c1.radio("Arrivo", ["Sabato", "Domenica"], horizontal=True, key="arr_fam")
            
            # Logica Letti
            opts = ["Tenda"]
            if rimasti >= num_persone: opts.insert(0, "Letto")
            else: st.warning(f"Rimasti solo {int(rimasti)} letti. Scegliete Tenda.")
            sistemazione = c2.radio("Sistemazione", opts, key="sis_fam")
            
            if st.form_submit_button("Conferma Prenotazione (Famiglia)"):
                salva_prenotazione(gruppo_scelto, riferimento, num_persone, arrivo, sistemazione)

    # --- TAB 2: EX SCOUT / ESTERNI ---
    with tab2:
        with st.form("form_esterni"):
            st.write("### Prenotazione Amici & Ex Scout")
            # Qui il nome è libero
            nome_manuale = st.text_input("Nome e Cognome di riferimento")
            
            num_persone_ex = st.number_input("Numero totale persone", min_value=1, value=1, key="n_ex")
            
            c1, c2 = st.columns(2)
            arrivo_ex = c1.radio("Arrivo", ["Sabato", "Domenica"], horizontal=True, key="arr_ex")
            
            # Logica Letti (identica)
            opts_ex = ["Tenda"]
            if rimasti >= num_persone_ex: opts_ex.insert(0, "Letto")
            else: st.warning(f"Rimasti solo {int(rimasti)} letti. Scegliete Tenda.")
            sistemazione_ex = c2.radio("Sistemazione", opts_ex, key="sis_ex")
            
            if st.form_submit_button("Conferma Prenotazione (Ex Scout)"):
                salva_prenotazione("Ex-Scout/Amico", nome_manuale, num_persone_ex, arrivo_ex, sistemazione_ex)

elif menu == "🔐 Area Staff":
    st.title("Admin - Visualizza Elenco")
    pwd = st.sidebar.text_input("Password Staff", type="password")
    
    if pwd == PASSWORD_STAFF:
        df = get_data()
        if not df.empty:
            st.dataframe(df) # Tabella semplice di sola lettura
            st.write(f"Totale persone prenotate: {df['Numero Persone'].sum()}")
    else:
        st.warning("Inserisci password staff.")
