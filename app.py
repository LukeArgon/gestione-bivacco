import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Prenotazioni Bivacco", page_icon="⛺", layout="wide")

# PASSWORD
PASSWORD_EVENTO = "fazzolettone2024" 
PASSWORD_STAFF = "capi123"

# POSTI LETTO TOTALI
POSTI_LETTO_TOTALI = 60

# LISTE GRUPPI (Modifica qui i nomi dei ragazzi)
# Nota: La lista "Ex-scout o Non" la lasciamo vuota qui perché la gestiamo diversamente nel codice
GRUPPI = {
    "Luna d'Argento": ["Bimbo A", "Bimbo B", "Bimbo C"], 
    "Mario Re": ["Bimbo D", "Bimbo E"],
    "Reparto": ["Marco", "Giulia", "Luca"],
    "Noviziato": ["Andrea", "Chiara"],
    "Clan": ["Rover 1", "Scolta 2"],
    "Ex-scout o Non": [] # Lasciare vuoto, gestito con casella di testo
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
@st.cache_resource
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
    return pd.DataFrame(sheet.get_all_records())

# --- 4. INTERFACCIA ---
menu = st.sidebar.radio("Menu", ["📝 Prenotazione", "🔐 Area Staff"])

if menu == "📝 Prenotazione":
    st.title("⛺ Prenotazione Bivacco")
    
    # --- CALCOLO POSTI RIMASTI ---
    df = get_data()
    posti_occupati = 0
    if not df.empty and "Sistemazione" in df.columns and "Numero Persone" in df.columns:
        # Filtra solo chi ha scelto Letto
        df_letti = df[df["Sistemazione"] == "Letto"]
        # Converte la colonna in numeri (per sicurezza) e fa la somma
        posti_occupati = pd.to_numeric(df_letti["Numero Persone"], errors='coerce').sum()
    
    rimasti = POSTI_LETTO_TOTALI - posti_occupati
    
    # Se il calcolo dà numeri strani (es. NaN), mettiamo 0
    if pd.isna(rimasti): rimasti = POSTI_LETTO_TOTALI

    col1, col2 = st.columns(2)
    col1.metric("Totale Letti", POSTI_LETTO_TOTALI)
    col2.metric("Letti Disponibili", int(rimasti))
    st.markdown("---")

    # --- MODULO ---
    with st.form("prenotazione"):
        # 1. Scelta Gruppo
        gruppo_scelto = st.selectbox("Seleziona", list(GRUPPI.keys()))
        
        # 2. Scelta Riferimento (Dinamica)
        if gruppo_scelto == "Ex-scout o Non":
            # Se è ex-scout, scrive a mano
            riferimento = st.text_input("Inserisci Nome di riferimento (es. Mario Rossi)")
        else:
            # Altrimenti sceglie dalla lista
            riferimento = st.selectbox("Riferimento (Ragazzo/a)", GRUPPI[gruppo_scelto])
            
        # 3. Numero Persone
        num_persone = st.number_input("Quante persone siete (incluso il riferimento)?", min_value=1, value=1, step=1)
        
        c1, c2 = st.columns(2)
        arrivo = c1.radio("Arrivo", ["Sabato", "Domenica"], horizontal=True)
        
        # 4. Sistemazione (Blocca Letto se pieni)
        opzioni = ["Tenda"]
        # Mostra l'opzione Letto solo se ci sono abbastanza posti per il gruppo inserito
        if rimasti >= num_persone:
            opzioni.insert(0, "Letto")
        elif rimasti > 0:
            st.warning(f"Sono rimasti solo {int(rimasti)} letti, ma voi siete in {num_persone}. Dovete scegliere Tenda o dividervi.")
        else:
            st.warning("⚠️ Letti esauriti.")
            
        sistemazione = c2.radio("Sistemazione", opzioni)
        
        if st.form_submit_button("Conferma Prenotazione"):
            if not riferimento:
                st.error("Inserisci un nome di riferimento!")
            else:
                # Prepara la riga ESATTA per le colonne del foglio Excel
                row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M"), # Data
                    gruppo_scelto,                             # Gruppo
                    riferimento,                               # Riferimento
                    num_persone,                               # Numero Persone
                    arrivo,                                    # Arrivo
                    "Letto" if "Letto" in sistemazione else "Tenda", # Sistemazione
                    "NO"                                       # Presente
                ]
                sheet.append_row(row)
                st.success("Prenotazione salvata!")
                st.rerun()

elif menu == "🔐 Area Staff":
    st.title("Gestione Presenze")
    pwd = st.sidebar.text_input("Password Staff", type="password")
    
    if pwd == PASSWORD_STAFF:
        df = get_data()
        if not df.empty:
            st.write("Usa il filtro per vedere un gruppo specifico.")
            filtro = st.selectbox("Filtra", ["Tutti"] + list(GRUPPI.keys()))
            
            df_view = df if filtro == "Tutti" else df[df["Gruppo"] == filtro]
            
            edited_df = st.data_editor(
                df_view,
                column_config={
                    "Presente": st.column_config.CheckboxColumn("Presente?", default=False)
                },
                disabled=["Data", "Gruppo", "Riferimento"],
                hide_index=True
            )
            
            if st.button("💾 Salva Modifiche"):
                # Per sicurezza, ricarica tutto e aggiorna
                # Metodo semplificato: Pulisce e riscrive.
                # Nota: Se usi i filtri, salva SOLO quando vedi "Tutti" per evitare di perdere righe nascoste.
                if filtro == "Tutti":
                    lista = [edited_df.columns.values.tolist()] + edited_df.values.tolist()
                    sheet.clear()
                    sheet.update(lista)
                    st.success("Salvato!")
                else:
                    st.warning("Per salvare, seleziona 'Tutti' nel filtro.")
    else:
        st.warning("Password necessaria.")
