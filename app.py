import math
import requests
import streamlit as st

# ==============================================================================
# CONFIGURAZIONE PAGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Tennis Analytics Engine Pro",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; }
    .value-box { background-color: #132e19; border: 1px solid #28a745; padding: 15px; border-radius: 8px; color: #28a745; }
    .no-value-box { background-color: #2c1214; border: 1px solid #dc3545; padding: 15px; border-radius: 8px; color: #dc3545; }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# CORE ENGINE (MATEMATICA & POISSON)
# ==============================================================================
def poisson_probability(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calculate_under_over(lmbda_total, line):
    prob_under = 0.0
    max_k = int(math.floor(line))
    for k in range(max_k + 1):
        prob_under += poisson_probability(lmbda_total, k)
    return prob_under, 1.0 - prob_under

def calculate_edge_and_kelly(prob_real, odds, bankroll):
    if odds <= 1.0:
        return 0.0, 0.0, 0.0
    edge = (prob_real * odds) - 1.0
    if edge > 0:
        b = odds - 1.0
        p = prob_real
        q = 1.0 - p
        kelly_full = (p * b - q) / b
        kelly_frac = max(0, kelly_full * 0.25)
        stake = bankroll * kelly_frac
    else:
        kelly_frac = 0.0
        stake = 0.0
    return edge * 100, kelly_frac * 100, stake


# ==============================================================================
# INTEGRATORE API AUTOMATICO (CORRETTO)
# ==============================================================================
@st.cache_data(ttl=300)
def fetch_live_matches_and_odds():
    matches = {}
    
    rapidapi_key = st.secrets.get("RAPIDAPI_KEY", None)
    odds_api_key = st.secrets.get("ODDS_API_KEY", None)

    # 1. Recupero da RapidAPI
    if rapidapi_key:
        try:
            url = "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/ms-api/upcoming/matches/atp"
            headers = {
                "X-RapidAPI-Key": rapidapi_key,
                "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com"
            }
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                events = data.get("data", []) if isinstance(data, dict) else data
                if isinstance(events, list) and len(events) > 0:
                    for ev in events:
                        p1 = ev.get("home_player", ev.get("player1", "Giocatore 1"))
                        p2 = ev.get("away_player", ev.get("player2", "Giocatore 2"))
                        tour = ev.get("tournament", "ATP Tour")
                        title = f"{p1} vs {p2} ({tour})"
                        
                        matches[title] = {
                            "p1": p1, "p2": p2, "tour": tour, "surf": ev.get("surface", "Hard"),
                            "elo1": 1650, "elo2": 1600,
                            "g1": 12.0, "g2": 10.5,
                            "ace1": 3.0, "ace2": 2.5,
                            "df1": 2.0, "df2": 2.5,
                            "o_win1": float(ev.get("odds_1", 1.75)),
                            "o_win2": float(ev.get("odds_2", 2.05)),
                            "o_u215": 1.80, "o_set20": 2.50
                        }
                    st.sidebar.success(f"✅ RapidAPI: {len(matches)} match caricati!")
        except Exception as e:
            st.sidebar.error(f"⚠️ Errore RapidAPI: {e}")

    # 2. Recupero dinamico da The-Odds-API (scansione tornei tennis attivi)
    if odds_api_key and not matches:
        try:
            # Trova la lista degli sport attivi per identificare i tornei di tennis disponibili
            sports_url = f"https://api.the-odds-api.com/v4/sports/?apiKey={odds_api_key}"
            sports_res = requests.get(sports_url, timeout=5)
            if sports_res.status_code == 200:
                tennis_sports = [s["key"] for s in sports_res.json() if "tennis" in s.get("group", "").lower() or "tennis" in s.get("key", "").lower()]
                
                for sport_key in tennis_sports[:2]: # Scansiona i primi tornei trovati
                    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={odds_api_key}&regions=eu&markets=h2h"
                    odds_res = requests.get(odds_url, timeout=5)
                    if odds_res.status_code == 200:
                        odds_data = odds_res.json()
                        for item in odds_data:
                            title = f"{item['home_team']} vs {item['away_team']} ({item.get('sport_title', 'Tennis')})"
                            if item.get("bookmakers"):
                                bm = item["bookmakers"][0]
                                h2h = next((m for m in bm["markets"] if m["key"] == "h2h"), None)
                                if h2h:
                                    p1_price = next((o["price"] for o in h2h["outcomes"] if o["name"] == item["home_team"]), 1.70)
                                    p2_price = next((o["price"] for o in h2h["outcomes"] if o["name"] == item["away_team"]), 2.10)
                                    matches[title] = {
                                        "p1": item["home_team"], "p2": item["away_team"],
                                        "tour": item.get("sport_title", "Tennis"), "surf": "Cemento/Terra",
                                        "elo1": 1680, "elo2": 1600,
                                        "g1": 12.5, "g2": 10.5, "ace1": 3.0, "ace2": 2.5, "df1": 2.0, "df2": 2.8,
                                        "o_win1": float(p1_price), "o_win2": float(p2_price),
                                        "o_u215": 1.83, "o_set20": 2.45
                                    }
                if matches:
                    st.sidebar.success(f"✅ The-Odds-API: {len(matches)} match live caricati!")
                else:
                    st.sidebar.info("ℹ️ Nessun match di tennis quotato attualmente su The-Odds-API.")
            else:
                st.sidebar.error(f"⚠️ Errore The-Odds-API ({sports_res.status_code}): Chiave API non valida o limite raggiunto.")
        except Exception as e:
            st.sidebar.error(f"⚠️ Errore Connessione The-Odds-API: {e}")

    # Fallback Database Demo (se nessuna API ha match attivi al momento)
    if not matches:
        st.sidebar.info("ℹ️ Nessun match live attualmente nei feed API. Caricato palinsesto di esempio.")
        matches = {
            "Mayar Sherif vs Elsa Jacquemot (WTA Amburgo)": {
                "p1": "Mayar Sherif", "p2": "Elsa Jacquemot", "tour": "WTA Amburgo", "surf": "Terra Battuta",
                "elo1": 1693, "elo2": 1518, "g1": 12.40, "g2": 8.10, "ace1": 1.8, "ace2": 1.4, "df1": 2.1, "df2": 3.8,
                "o_win1": 1.39, "o_win2": 3.01, "o_u215": 1.765, "o_set20": 1.95
            },
            "Paula Badosa vs Panna Udvardy (WTA Iasi)": {
                "p1": "Paula Badosa", "p2": "Panna Udvardy", "tour": "WTA Iasi", "surf": "Terra Battuta",
                "elo1": 1610, "elo2": 1580, "g1": 11.80, "g2": 12.60, "ace1": 2.0, "ace2": 1.5, "df1": 4.1, "df2": 2.2,
                "o_win1": 1.52, "o_win2": 2.48, "o_u215": 1.85, "o_set20": 2.20
            },
            "Carlos Alcaraz vs Novak Djokovic (ATP)": {
                "p1": "Carlos Alcaraz", "p2": "Novak Djokovic", "tour": "ATP Tour", "surf": "Terra Battuta",
                "elo1": 2050, "elo2": 2010, "g1": 13.10, "g2": 12.20, "ace1": 4.5, "ace2": 5.8, "df1": 2.0, "df2": 1.8,
                "o_win1": 1.68, "o_win2": 2.25, "o_u215": 1.55, "o_set20": 2.60
            },
            "Jannik Sinner vs Daniil Medvedev (ATP)": {
                "p1": "Jannik Sinner", "p2": "Daniil Medvedev", "tour": "ATP Masters", "surf": "Cemento",
                "elo1": 2080, "elo2": 1940, "g1": 13.50, "g2": 10.80, "ace1": 7.2, "ace2": 8.1, "df1": 1.5, "df2": 3.2,
                "o_win1": 1.33, "o_win2": 3.40, "o_u215": 1.80, "o_set20": 1.85
            }
        }
    return matches


# ==============================================================================
# UI STREAMLIT (INTERFACCIA GRAFICA)
# ==============================================================================
st.title("🎾 Tennis Value Analytics Engine Pro")
st.caption("Engine Quantitativo con Distribuzione di Poisson, Kelly Criterion & Live API")

st.sidebar.header("⚙️ Seleziona Match & Parametri")
matches_db = fetch_live_matches_and_odds()

selected_match_key = st.sidebar.selectbox("Partite del Giorno:", list(matches_db.keys()))
m = matches_db[selected_match_key]

bankroll = st.sidebar.number_input("Il tuo Bankroll Totale (€):", value=1000, step=50)

st.subheader(f"📊 Analisi: {m['p1']} vs {m['p2']}")
st.markdown(f"**Torneo:** {m['tour']} | **Superficie:** {m['surf']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric(f"Surface ELO {m['p1']}", m["elo1"])
col2.metric(f"Surface ELO {m['p2']}", m["elo2"])
col3.metric("Game Totali Attesi", f"{m['g1'] + m['g2']:.2f}")
col4.metric("Divario ELO", f"{m['elo1'] - m['elo2']:+} pts")

st.divider()

tab1, tab2, tab3 = st.tabs(["🧮 Previsioni & Poisson", "💰 Value Finder & Stake", "🎙️ Betting Mindset"])

with tab1:
    tot_games = m["g1"] + m["g2"]
    prob_u215, prob_o215 = calculate_under_over(tot_games, 21.5)
    tot_aces = m["ace1"] + m["ace2"]
    prob_u35_ace, _ = calculate_under_over(tot_aces, 3.5)
    tot_df = m["df1"] + m["df2"]
    _, prob_o45_df = calculate_under_over(tot_df, 4.5)
    
    st.table({
        "Categoria Statistica": ["Game Vinti Previsti", "Ace Serviti Previsti", "Doppi Falli Commessi", "Under/Over Game (Linea 21.5)"],
        f"{m['p1']}": [f"{m['g1']:.2f}", f"{m['ace1']:.2f}", f"{m['df1']:.2f}", "-"],
        f"{m['p2']}": [f"{m['g2']:.2f}", f"{m['ace2']:.2f}", f"{m['df2']:.2f}", "-"],
        "Totale Match Atteso": [f"{tot_games:.2f}", f"{tot_aces:.2f}", f"{tot_df:.2f}", f"Under 21.5: {prob_u215*100:.1f}%"]
    })

with tab2:
    edge_u215, kelly_u215, stake_u215 = calculate_edge_and_kelly(prob_u215, m["o_u215"], bankroll)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("#### 🟢 Bet Principale: Under 21.5 Game Totali")
        st.write(f"**Quota Bookmaker:** {m['o_u215']}")
        st.write(f"**Probabilità Modello:** {prob_u215*100:.1f}%")
        st.write(f"**Edge (% Valore):** {edge_u215:+.2f}%")
        if edge_u215 > 0:
            st.markdown(f"<div class='value-box'><b>VALUE BET TROVATA!</b><br>Stake Consigliato: <b>{stake_u215:.2f}€</b> ({kelly_u215:.1f}% Bankroll)</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-value-box'>NO VALUE - Quota troppo bassa</div>", unsafe_allow_html=True)

with tab3:
    st.info(f"Analisi operativa per {m['p1']} vs {m['p2']}: Quota raccomandata per Under 21.5 game a {m['o_u215']} con edge del {edge_u215:+.2f}%.")
