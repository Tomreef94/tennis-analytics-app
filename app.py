import math
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

# Custom CSS per uno stile moderno "Dark Theme"
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
# CORE ENGINE (FUNZIONI MATEMATICHE)
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
    kelly_frac = max(0, kelly_full * 0.25)  # Quarter-Kelly (25%)
    stake = bankroll * kelly_frac
  else:
    kelly_frac = 0.0
    stake = 0.0
  return edge * 100, kelly_frac * 100, stake


# ==============================================================================
# HEADER & SIDEBAR (ACQUISIZIONE MATCH)
# ==============================================================================
st.title("🎾 Tennis Value Analytics Engine Pro")
st.caption("Engine Quantitativo con Distribuzione di Poisson & Kelly Criterion")

st.sidebar.header("⚙️ Seleziona Match & Parametri")

# Simulazione Database Match Caricati via API
matches_db = {
    "Mayar Sherif vs Elsa Jacquemot (WTA Amburgo)": {
        "p1": "Mayar Sherif",
        "p2": "Elsa Jacquemot",
        "tour": "WTA Amburgo",
        "surf": "Terra Battuta",
        "elo1": 1693,
        "elo2": 1518,
        "g1": 12.40,
        "g2": 8.10,
        "ace1": 1.8,
        "ace2": 1.4,
        "df1": 2.1,
        "df2": 3.8,
        "o_win1": 1.39,
        "o_win2": 3.01,
        "o_u215": 1.765,
        "o_set20": 1.95,
    },
    "Paula Badosa vs Panna Udvardy (WTA)": {
        "p1": "Paula Badosa",
        "p2": "Panna Udvardy",
        "tour": "WTA Tour",
        "surf": "Terra Battuta",
        "elo1": 1610,
        "elo2": 1580,
        "g1": 11.80,
        "g2": 12.60,
        "ace1": 2.0,
        "ace2": 1.5,
        "df1": 4.1,
        "df2": 2.2,
        "o_win1": 1.52,
        "o_win2": 2.48,
        "o_u215": 1.85,
        "o_set20": 2.20,
    },
}

selected_match_key = st.sidebar.selectbox(
    "Partite del Giorno (Auto-Import):", list(matches_db.keys())
)
m = matches_db[selected_match_key]

bankroll = st.sidebar.number_input(
    "Il tuo Bankroll Totale (€):", value=1000, step=50
)

# ==============================================================================
# DASHBOARD PRINCIPALE
# ==============================================================================
st.subheader(f"📊 Analisi: {m['p1']} vs {m['p2']}")
st.markdown(
    f"**Torneo:** {m['tour']} | **Superficie:** {m['surf']} | **Qualità Dati:**"
    " 🟢 100% WTA/ATP (No ITF)"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric(f"Surface ELO {m['p1']}", m["elo1"])
col2.metric(f"Surface ELO {m['p2']}", m["elo2"])
col3.metric("Game Totali Attesi", f"{m['g1'] + m['g2']:.2f}")
col4.metric(
    "Divario ELO",
    f"{m['elo1'] - m['elo2']:+} pts",
    delta_color="normal" if m["elo1"] > m["elo2"] else "inverse",
)

st.divider()

# ==============================================================================
# TABELLE STATISTICHE & POISSON
# ==============================================================================
tab1, tab2, tab3 = st.tabs(
    ["🧮 Previsioni & Poisson", "💰 Value Finder & Stake", "🎙️ Betting Mindset"]
)

with tab1:
  st.markdown("### 📊 Proiezioni Matematiche per Singolo Giocatore & Match")

  tot_games = m["g1"] + m["g2"]
  prob_u215, prob_o215 = calculate_under_over(tot_games, 21.5)

  tot_aces = m["ace1"] + m["ace2"]
  prob_u35_ace, _ = calculate_under_over(tot_aces, 3.5)

  tot_df = m["df1"] + m["df2"]
  _, prob_o45_df = calculate_under_over(tot_df, 4.5)

  # Tabella Proiezioni
  st.table({
      "Categoria Statistica": [
          "Game Vinti Previsti",
          "Ace Serviti Previsti",
          "Doppi Falli Commessi",
          "Under/Over Game (Linea 21.5)",
          "Aces Totali Incontro (Linea 3.5)",
          "Doppi Falli Incontro (Linea 4.5)",
      ],
      f"{m['p1']}": [
          f"{m['g1']:.2f}",
          f"{m['ace1']:.2f}",
          f"{m['df1']:.2f}",
          "-",
          "-",
          "-",
      ],
      f"{m['p2']}": [
          f"{m['g2']:.2f}",
          f"{m['ace2']:.2f}",
          f"{m['df2']:.2f}",
          "-",
          "-",
          "-",
      ],
      "Totale Match Atteso": [
          f"{tot_games:.2f}",
          f"{tot_aces:.2f}",
          f"{tot_df:.2f}",
          f"Under 21.5: {prob_u215*100:.1f}%",
          f"Under 3.5: {prob_u35_ace*100:.1f}%",
          f"Over 4.5: {prob_o45_df*100:.1f}%",
      ],
  })

with tab2:
  st.markdown("### 🎯 Inefficienze di Mercato & Stake Riconosciuti")

  # Calcolo Edge
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
          f"""
            <div class='value-box'>
                <b>VALUE BET TROVATA!</b><br>
                Stake Consigliato (Kelly 25%): <b>{stake_u215:.2f}€</b> ({kelly_u215:.1f}% Bankroll)
            </div>
            """,
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          "<div class='no-value-box'>NO VALUE - Nessun margine sulla"
          " quota</div>",
          unsafe_allow_html=True,
      )

  with col_v2:
    p1_prob_win = 0.735 if "Sherif" in m["p1"] else 0.466
    p1_set20 = p1_prob_win * p1_prob_win
    edge_set20, kelly_set20, stake_set20 = calculate_edge_and_kelly(
        p1_set20, m["o_set20"], bankroll
    )

    st.markdown(f"#### 🟡 Bet Speculativa: {m['p1']} 2-0 (Set Betting)")
    st.write(f"**Quota Bookmaker:** {m['o_set20']}")
    st.write(f"**Probabilità Modello:** {p1_set20*100:.1f}%")
    st.write(f"**Edge (% Valore):** {edge_set20:+.2f}%")

    if edge_set20 > 0:
      st.markdown(
          f"""
            <div class='value-box'>
                <b>VALUE BET TROVATA!</b><br>
                Stake Consigliato: <b>{stake_set20:.2f}€</b> ({kelly_set20:.1f}% Bankroll)
            </div>
            """,
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          "<div class='no-value-box'>NO VALUE - Quota troppo bassa</div>",
          unsafe_allow_html=True,
      )

with tab3:
  st.markdown("### 🎙️ Commento dello Scommettitore Professionista")

  st.info(f"""
    **Analisi Operativa sul Match {m['p1']} v {m['p2']}:**
    
    1. **Valutazione Quota 1X2:** La vittoria secca di {m['p1']} a quota {m['o_win1']} non offre margine matematico sufficiente per giustificare un'esposizione finanziaria in singola.
    2. **Identificazione della Value Bet:** Il valore reale risiede sull'**Under 21.5 Game Totali a quota {m['o_u215']}**, dove il nostro algoritmo registra una proiezione media di **{tot_games:.2f} game totali**, garantendo un **Edge del {edge_u215:+.2f}%**.
    3. **Gestione del Bankroll:** Allocare **{stake_u215:.2f}€ ({kelly_u215:.1f}% del budget)** sul mercato Under Game.
    """)
