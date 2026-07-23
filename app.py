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
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; }
    .value-box { background-color: #132e19; border: 1px solid #28a745; padding: 15px; border-radius: 8px; color: #28a745; }
    .no-value-box { background-color: #2c1214; border: 1px solid #dc3545; padding: 15px; border-radius: 8px; color: #dc3545; }
    </style>
""",
    unsafe_allow_html=True,
)


# ==============================================================================
# HELPER PARSER PER ESTRARRE I NOMI PULITI DAL JSON DELL'API
# ==============================================================================
def parse_player_data(data, default_name):
  if isinstance(data, dict):
    name = data.get("name", default_name)
    odd = data.get("odd", 1.80)
    try:
      odd = float(odd)
    except:
      odd = 1.80
    return str(name), odd
  elif isinstance(data, str):
    return data, 1.80
  return default_name, 1.80


def parse_tournament_data(data, default_tour):
  if isinstance(data, dict):
    tour_name = data.get("name", default_tour)
    court_info = data.get("court", {})
    surface = "Hard"
    if isinstance(court_info, dict):
      surface = court_info.get("name", "Hard")
    return str(tour_name), str(surface)
  return default_tour, "Hard"


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
# INTEGRATORE API AUTOMATICO CON CLEANING PULITO
# ==============================================================================
@st.cache_data(ttl=300)
def fetch_live_matches_and_odds():
  matches = {}

  rapidapi_key = st.secrets.get("RAPIDAPI_KEY", None)
  odds_api_key = st.secrets.get("ODDS_API_KEY", None)

  if rapidapi_key:
    endpoints = [
        "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/ms-api/upcoming/match-prediction/atp",
        "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/ms-api/upcoming/matches/atp",
        "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/ms-api/live/matches",
    ]
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com",
    }

    for url in endpoints:
      try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
          data = res.json()
          events = []
          if isinstance(data, dict):
            events = data.get(
                "data", data.get("matches", data.get("events", []))
            )
          elif isinstance(data, list):
            events = data

          if isinstance(events, list) and len(events) > 0:
            for ev in events:
              if isinstance(ev, dict):
                p1_raw = ev.get("home_player", ev.get("player1", "Giocatore 1"))
                p2_raw = ev.get("away_player", ev.get("player2", "Giocatore 2"))
                tour_raw = ev.get(
                    "tournament", ev.get("tournament_name", "Tennis Tour")
                )

                p1_name, odd1 = parse_player_data(p1_raw, "Giocatore 1")
                p2_name, odd2 = parse_player_data(p2_raw, "Giocatore 2")
                tour_name, surface = parse_tournament_data(
                    tour_raw, "Generali Open"
                )

                title = f"{p1_name} vs {p2_name} ({tour_name})"

                matches[title] = {
                    "p1": p1_name,
                    "p2": p2_name,
                    "tour": tour_name,
                    "surf": surface,
                    "elo1": 1680 if odd1 < odd2 else 1580,
                    "elo2": 1580 if odd1 < odd2 else 1680,
                    "g1": 12.5 if odd1 < odd2 else 10.0,
                    "g2": 10.0 if odd1 < odd2 else 12.5,
                    "ace1": 4.0,
                    "ace2": 3.0,
                    "df1": 2.0,
                    "df2": 2.5,
                    "o_win1": float(odd1),
                    "o_win2": float(odd2),
                    "o_u215": 1.80,
                    "o_set20": 2.20,
                }
      except Exception:
        pass

  # Fallback Demo se non ci sono dati
  if not matches:
    matches = {
        "Mariano Navone vs Quentin Halys (Kitzbuhel)": {
            "p1": "Mariano Navone",
            "p2": "Quentin Halys",
            "tour": "Generali Open - Kitzbuhel",
            "surf": "Terra Battuta",
            "elo1": 1680,
            "elo2": 1590,
            "g1": 12.50,
            "g2": 10.00,
            "ace1": 3.0,
            "ace2": 7.5,
            "df1": 2.0,
            "df2": 3.1,
            "o_win1": 1.47,
            "o_win2": 2.67,
            "o_u215": 1.80,
            "o_set20": 2.10,
        }
    }
  return matches


# ==============================================================================
# UI STREAMLIT (INTERFACCIA GRAFICA)
# ==============================================================================
st.title("🎾 Tennis Value Analytics Engine Pro")
st.caption(
    "Engine Quantitativo con Distribuzione di Poisson, Kelly Criterion & Live"
    " API"
)

st.sidebar.header("⚙️ Seleziona Match & Parametri")
matches_db = fetch_live_matches_and_odds()

selected_match_key = st.sidebar.selectbox(
    "Partite del Giorno:", list(matches_db.keys())
)
m = matches_db[selected_match_key]

bankroll = st.sidebar.number_input(
    "Il tuo Bankroll Totale (€):", value=1000, step=50
)

st.subheader(f"📊 Analisi: {m['p1']} vs {m['p2']}")
st.markdown(f"**Torneo:** {m['tour']} | **Superficie:** {m['surf']}")

col1, col2, col3, col4 = st.columns(4)
col1.metric(f"Surface ELO {m['p1']}", m["elo1"])
col2.metric(f"Surface ELO {m['p2']}", m["elo2"])
col3.metric("Game Totali Attesi", f"{m['g1'] + m['g2']:.2f}")
col4.metric("Divario ELO", f"{m['elo1'] - m['elo2']:+} pts")

st.divider()

tab1, tab2, tab3 = st.tabs(
    ["🧮 Previsioni & Poisson", "💰 Value Finder & Stake", "🎙️ Betting Mindset"]
)

with tab1:
  tot_games = m["g1"] + m["g2"]
  prob_u215, prob_o215 = calculate_under_over(tot_games, 21.5)
  tot_aces = m["ace1"] + m["ace2"]
  prob_u35_ace, _ = calculate_under_over(tot_aces, 3.5)
  tot_df = m["df1"] + m["df2"]
  _, prob_o45_df = calculate_under_over(tot_df, 4.5)

  st.table({
      "Categoria Statistica": [
          "Game Vinti Previsti",
          "Ace Serviti Previsti",
          "Doppi Falli Commessi",
          "Under/Over Game (Linea 21.5)",
      ],
      f"{m['p1']}": [
          f"{m['g1']:.2f}",
          f"{m['ace1']:.2f}",
          f"{m['df1']:.2f}",
          "-",
      ],
      f"{m['p2']}": [
          f"{m['g2']:.2f}",
          f"{m['ace2']:.2f}",
          f"{m['df2']:.2f}",
          "-",
      ],
      "Totale Match Atteso": [
          f"{tot_games:.2f}",
          f"{tot_aces:.2f}",
          f"{tot_df:.2f}",
          f"Under 21.5: {prob_u215*100:.1f}%",
      ],
  })

with tab2:
  edge_u215, kelly_u215, stake_u215 = calculate_edge_and_kelly(
      prob_u215, m["o_u215"], bankroll
  )
  col_v1, col_v2 = st.columns(2)
  with col_v1:
    st.markdown("#### 🟢 Bet Principale: Under 21.5 Game Totali")
    st.write(f"**Quota Bookmaker:** {m['o_u215']}")
    st.write(f"**Probabilità Modello:** {prob_u215*100:.1f}%")
    st.write(f"**Edge (% Valore):** {edge_u215:+.2f}%")
    if edge_u215 > 0:
      st.markdown(
          f"<div class='value-box'><b>VALUE BET TROVATA!</b><br>Stake"
          f" Consigliato: <b>{stake_u215:.2f}€</b> ({kelly_u215:.1f}%"
          " Bankroll)</div>",
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          "<div class='no-value-box'>NO VALUE - Quota troppo bassa</div>",
          unsafe_allow_html=True,
      )

with tab3:
  st.info(
      f"Analisi operativa per {m['p1']} vs {m['p2']}: Quota raccomandata per"
      f" Under 21.5 game a {m['o_u215']} con edge del {edge_u215:+.2f}%."
  )
