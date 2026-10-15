"""Universo di strumenti monitorati da Quadrante.

Ogni voce: (ticker Yahoo, nome, tipo, paese)
Tipi: Azione, ETF, Indice, Cripto, Forex, Materia prima
Aggiungi o togli righe liberamente: lo script ignora i ticker che Yahoo non restituisce.
"""

# --------------------------------------------------------------------------
# Gruppi della "Panoramica mercati" (ordine = ordine delle tabelle)
# --------------------------------------------------------------------------
GROUPS = {
    "usa": ("USA", [
        ("^GSPC", "S&P 500", "Indice", "Stati Uniti"),
        ("^NDX", "Nasdaq 100", "Indice", "Stati Uniti"),
        ("^RUT", "Russell 2000", "Indice", "Stati Uniti"),
        ("^DJI", "Dow Jones", "Indice", "Stati Uniti"),
    ]),
    "europa": ("Europa", [
        ("^STOXX50E", "Euro Stoxx 50", "Indice", "Eurozona"),
        ("^GDAXI", "DAX 40", "Indice", "Germania"),
        ("FTSEMIB.MI", "FTSE MIB", "Indice", "Italia"),
        ("^FCHI", "CAC 40", "Indice", "Francia"),
        ("^FTSE", "FTSE 100", "Indice", "Regno Unito"),
        ("^IBEX", "IBEX 35", "Indice", "Spagna"),
        ("^SSMI", "SMI", "Indice", "Svizzera"),
        ("^AEX", "AEX", "Indice", "Paesi Bassi"),
    ]),
    "asia": ("Asia", [
        ("^N225", "Nikkei 225", "Indice", "Giappone"),
        ("^HSI", "Hang Seng", "Indice", "Hong Kong"),
        ("000001.SS", "Shanghai Composite", "Indice", "Cina"),
        ("^KS11", "KOSPI", "Indice", "Corea del Sud"),
        ("^TWII", "Taiwan Weighted", "Indice", "Taiwan"),
        ("^NSEI", "Nifty 50", "Indice", "India"),
    ]),
    "emergenti": ("Mercati emergenti", [
        ("EEM", "MSCI Emerging Markets", "ETF", "Globale"),
        ("^BVSP", "Bovespa", "Indice", "Brasile"),
        ("^MXX", "IPC Messico", "Indice", "Messico"),
        ("^MERV", "Merval", "Indice", "Argentina"),
        ("EZA", "MSCI Sudafrica", "ETF", "Sudafrica"),
        ("TUR", "MSCI Turchia", "ETF", "Turchia"),
        ("EIDO", "MSCI Indonesia", "ETF", "Indonesia"),
    ]),
    "sviluppati": ("Mercati sviluppati", [
        ("URTH", "MSCI World", "ETF", "Globale"),
        ("EFA", "MSCI EAFE", "ETF", "Globale"),
        ("^GSPTSE", "S&P/TSX", "Indice", "Canada"),
        ("^AXJO", "ASX 200", "Indice", "Australia"),
        ("EWJ", "MSCI Giappone", "ETF", "Giappone"),
        ("VGK", "FTSE Europe", "ETF", "Eurozona"),
    ]),
    "forex": ("Forex", [
        ("EURUSD=X", "EUR/USD", "Forex", "Globale"),
        ("GBPUSD=X", "GBP/USD", "Forex", "Globale"),
        ("USDJPY=X", "USD/JPY", "Forex", "Globale"),
        ("USDCHF=X", "USD/CHF", "Forex", "Globale"),
        ("USDCAD=X", "USD/CAD", "Forex", "Globale"),
        ("AUDUSD=X", "AUD/USD", "Forex", "Globale"),
        ("EURJPY=X", "EUR/JPY", "Forex", "Globale"),
        ("GBPJPY=X", "GBP/JPY", "Forex", "Globale"),
        ("AUDJPY=X", "AUD/JPY", "Forex", "Globale"),
        ("EURCHF=X", "EUR/CHF", "Forex", "Globale"),
        ("EURGBP=X", "EUR/GBP", "Forex", "Globale"),
        ("DX-Y.NYB", "Dollar Index", "Forex", "Globale"),
    ]),
    "cripto": ("Cripto", [
        ("BTC-USD", "Bitcoin", "Cripto", "Globale"),
        ("ETH-USD", "Ethereum", "Cripto", "Globale"),
        ("SOL-USD", "Solana", "Cripto", "Globale"),
        ("XRP-USD", "XRP", "Cripto", "Globale"),
        ("BNB-USD", "BNB", "Cripto", "Globale"),
        ("ADA-USD", "Cardano", "Cripto", "Globale"),
        ("DOGE-USD", "Dogecoin", "Cripto", "Globale"),
        ("LINK-USD", "Chainlink", "Cripto", "Globale"),
    ]),
    "obbligazioni": ("Obbligazioni", [
        ("TLT", "Treasury USA 20+ anni", "ETF", "Stati Uniti"),
        ("IEF", "Treasury USA 7-10 anni", "ETF", "Stati Uniti"),
        ("SHY", "Treasury USA 1-3 anni", "ETF", "Stati Uniti"),
        ("TIP", "TIPS USA (inflazione)", "ETF", "Stati Uniti"),
        ("LQD", "Corporate Investment Grade", "ETF", "Stati Uniti"),
        ("HYG", "Corporate High Yield", "ETF", "Stati Uniti"),
        ("EMB", "Bond emergenti USD", "ETF", "Globale"),
        ("BWX", "Governativi internazionali", "ETF", "Globale"),
    ]),
    "materie": ("Materie prime", [
        ("GC=F", "Oro", "Materia prima", "Globale"),
        ("SI=F", "Argento", "Materia prima", "Globale"),
        ("PL=F", "Platino", "Materia prima", "Globale"),
        ("HG=F", "Rame", "Materia prima", "Globale"),
        ("CL=F", "Petrolio WTI", "Materia prima", "Globale"),
        ("BZ=F", "Petrolio Brent", "Materia prima", "Globale"),
        ("NG=F", "Gas naturale", "Materia prima", "Globale"),
        ("ZW=F", "Grano", "Materia prima", "Globale"),
        ("ZC=F", "Mais", "Materia prima", "Globale"),
        ("DBC", "Paniere materie prime", "ETF", "Globale"),
    ]),
    "fattori": ("Fattori", [
        ("MGC", "Mega capitalizzazione", "ETF", "Stati Uniti"),
        ("IWB", "Grande capitalizzazione", "ETF", "Stati Uniti"),
        ("IWR", "Media capitalizzazione", "ETF", "Stati Uniti"),
        ("IWM", "Piccola capitalizzazione", "ETF", "Stati Uniti"),
        ("QUAL", "Alta qualità", "ETF", "Stati Uniti"),
        ("VTV", "Value", "ETF", "Stati Uniti"),
        ("VUG", "Growth", "ETF", "Stati Uniti"),
        ("SPHB", "Alto beta", "ETF", "Stati Uniti"),
        ("MTUM", "Momentum", "ETF", "Stati Uniti"),
        ("USMV", "Bassa volatilità", "ETF", "Stati Uniti"),
        ("VYM", "Alto dividendo", "ETF", "Stati Uniti"),
    ]),
    "settori": ("Settori USA", [
        ("XLK", "Tecnologia", "ETF", "Stati Uniti"),
        ("XLC", "Comunicazione", "ETF", "Stati Uniti"),
        ("XLY", "Consumi discrezionali", "ETF", "Stati Uniti"),
        ("XLP", "Beni di prima necessità", "ETF", "Stati Uniti"),
        ("XLF", "Finanziari", "ETF", "Stati Uniti"),
        ("XLV", "Sanità", "ETF", "Stati Uniti"),
        ("XLI", "Industriali", "ETF", "Stati Uniti"),
        ("XLE", "Energia", "ETF", "Stati Uniti"),
        ("XLB", "Materiali", "ETF", "Stati Uniti"),
        ("XLU", "Utility", "ETF", "Stati Uniti"),
        ("XLRE", "Immobiliare", "ETF", "Stati Uniti"),
    ]),
}

# Pannelli a schede: quali gruppi stanno insieme
PANELS = [
    ["usa", "europa", "asia", "emergenti", "sviluppati"],
    ["forex", "cripto", "obbligazioni", "materie"],
    ["fattori", "settori"],
]

# --------------------------------------------------------------------------
# Azioni ed ETF aggiuntivi per lo screener
# --------------------------------------------------------------------------
_US = """AAPL Apple|MSFT Microsoft|NVDA NVIDIA|AMZN Amazon|GOOGL Alphabet|META Meta Platforms|TSLA Tesla|BRK-B Berkshire Hathaway|
JPM JPMorgan Chase|V Visa|MA Mastercard|UNH UnitedHealth|XOM Exxon Mobil|JNJ Johnson & Johnson|WMT Walmart|PG Procter & Gamble|
AVGO Broadcom|HD Home Depot|CVX Chevron|MRK Merck|ABBV AbbVie|KO Coca-Cola|PEP PepsiCo|COST Costco|LLY Eli Lilly|ADBE Adobe|
CRM Salesforce|NFLX Netflix|AMD AMD|INTC Intel|CSCO Cisco|ORCL Oracle|TMO Thermo Fisher|ABT Abbott|MCD McDonald's|DIS Disney|
BAC Bank of America|WFC Wells Fargo|GS Goldman Sachs|MS Morgan Stanley|CAT Caterpillar|DE Deere|HON Honeywell|GE GE Aerospace|
BA Boeing|IBM IBM|QCOM Qualcomm|TXN Texas Instruments|AMGN Amgen|PFE Pfizer|NKE Nike|SBUX Starbucks|LOW Lowe's|UPS UPS|
RTX RTX|LMT Lockheed Martin|NEE NextEra Energy|DUK Duke Energy|SO Southern Co|T AT&T|VZ Verizon|CMCSA Comcast|PM Philip Morris|
MDT Medtronic|ISRG Intuitive Surgical|GILD Gilead|BKNG Booking|BLK BlackRock|C Citigroup|AXP American Express|SCHW Charles Schwab|
SPGI S&P Global|INTU Intuit|NOW ServiceNow|AMAT Applied Materials|MU Micron|LRCX Lam Research|KLAC KLA|PANW Palo Alto Networks|
UBER Uber|PYPL PayPal|F Ford|GM General Motors|COP ConocoPhillips|SLB Schlumberger|LIN Linde|SHW Sherwin-Williams|PLD Prologis|
AMT American Tower|EQIX Equinix|PLTR Palantir|KEYS Keysight|MATX Matson|ANET Arista Networks|CRWD CrowdStrike|VRTX Vertex|REGN Regeneron"""

_IT = """ENI.MI Eni|ENEL.MI Enel|ISP.MI Intesa Sanpaolo|UCG.MI UniCredit|STLAM.MI Stellantis|G.MI Generali|RACE.MI Ferrari|
STMMI.MI STMicroelectronics|TIT.MI Telecom Italia|PRY.MI Prysmian|MB.MI Mediobanca|BAMI.MI Banco BPM|BMPS.MI Monte dei Paschi|
BPE.MI BPER Banca|CPR.MI Campari|DIA.MI DiaSorin|A2A.MI A2A|AMP.MI Amplifon|AZM.MI Azimut|BZU.MI Buzzi|FBK.MI FinecoBank|
HER.MI Hera|IG.MI Italgas|INW.MI Inwit|IP.MI Interpump|LDO.MI Leonardo|MONC.MI Moncler|NEXI.MI Nexi|PIRC.MI Pirelli|
PST.MI Poste Italiane|REC.MI Recordati|SPM.MI Saipem|SRG.MI Snam|TEN.MI Tenaris|TRN.MI Terna|UNI.MI Unipol|IVG.MI Iveco|
BC.MI Brunello Cucinelli|ERG.MI ERG|BMED.MI Banca Mediolanum"""

_EU = """ASML.AS ASML|SAP.DE SAP|MC.PA LVMH|SIE.DE Siemens|TTE.PA TotalEnergies|ALV.DE Allianz|SAN.PA Sanofi|OR.PA L'Oréal|
AIR.PA Airbus|SU.PA Schneider Electric|DTE.DE Deutsche Telekom|IBE.MC Iberdrola|SAN.MC Banco Santander|BNP.PA BNP Paribas|
ABI.BR AB InBev|CS.PA AXA|ITX.MC Inditex|MUV2.DE Munich Re|RMS.PA Hermès|EL.PA EssilorLuxottica|DG.PA Vinci|BAS.DE BASF|
BAYN.DE Bayer|ADS.DE Adidas|MBG.DE Mercedes-Benz|BMW.DE BMW|VOW3.DE Volkswagen|INGA.AS ING|AD.AS Ahold Delhaize|
PRX.AS Prosus|KER.PA Kering|SAF.PA Safran|BBVA.MC BBVA|DB1.DE Deutsche Börse|IFX.DE Infineon|NOKIA.HE Nokia|RI.PA Pernod Ricard|
AI.PA Air Liquide|RHM.DE Rheinmetall|ENR.DE Siemens Energy|ENA.MC Endesa"""

_COUNTRY_BY_SUFFIX = {".MI": "Italia", ".DE": "Germania", ".PA": "Francia", ".AS": "Paesi Bassi",
                      ".MC": "Spagna", ".BR": "Belgio", ".HE": "Finlandia"}

_ETF_EXTRA = [
    ("SPY", "SPDR S&P 500", "Stati Uniti"), ("QQQ", "Invesco QQQ", "Stati Uniti"),
    ("SMH", "Semiconduttori", "Stati Uniti"), ("ARKK", "ARK Innovation", "Stati Uniti"),
    ("ICLN", "Energia pulita globale", "Globale"), ("TAN", "Solare", "Globale"),
    ("URA", "Uranio", "Globale"), ("LIT", "Litio e batterie", "Globale"),
    ("BOTZ", "Robotica e IA", "Globale"), ("CIBR", "Cybersecurity", "Globale"),
    ("GDX", "Minatori d'oro", "Globale"), ("ITA", "Aerospazio e difesa", "Stati Uniti"),
    ("XBI", "Biotech", "Stati Uniti"), ("KRE", "Banche regionali", "Stati Uniti"),
    ("MCHI", "MSCI Cina", "Cina"), ("INDA", "MSCI India", "India"),
    ("EWZ", "MSCI Brasile", "Brasile"), ("EWW", "MSCI Messico", "Messico"),
    ("EWI", "MSCI Italia", "Italia"), ("EWG", "MSCI Germania", "Germania"),
    ("EWU", "MSCI Regno Unito", "Regno Unito"), ("EWC", "MSCI Canada", "Canada"),
    ("EWA", "MSCI Australia", "Australia"), ("EWY", "MSCI Corea", "Corea del Sud"),
    ("EWT", "MSCI Taiwan", "Taiwan"), ("GLD", "Oro fisico", "Globale"),
    ("SLV", "Argento fisico", "Globale"), ("UUP", "Dollaro USA long", "Stati Uniti"),
]


# --------------------------------------------------------------------------
# Temi di investimento (ETF tematici)
# --------------------------------------------------------------------------
THEMES = {
    "Intelligenza artificiale e robotica": [("BOTZ", "Global X Robotics & AI"), ("ROBO", "ROBO Global Robotics"), ("AIQ", "Global X AI & Technology")],
    "Semiconduttori": [("SMH", "VanEck Semiconductor"), ("SOXX", "iShares Semiconductor")],
    "Cybersecurity": [("CIBR", "First Trust Cybersecurity"), ("HACK", "Amplify Cybersecurity")],
    "Cloud e software": [("SKYY", "First Trust Cloud Computing"), ("IGV", "iShares Software")],
    "Energia pulita": [("ICLN", "iShares Global Clean Energy"), ("TAN", "Invesco Solar"), ("QCLN", "First Trust Clean Edge")],
    "Uranio e nucleare": [("URA", "Global X Uranium"), ("NLR", "VanEck Uranium & Nuclear")],
    "Litio e batterie": [("LIT", "Global X Lithium & Battery")],
    "Aerospazio e difesa": [("ITA", "iShares Aerospace & Defense"), ("XAR", "SPDR Aerospace & Defense")],
    "Biotecnologie": [("XBI", "SPDR Biotech"), ("IBB", "iShares Biotechnology")],
    "Fintech": [("FINX", "Global X FinTech"), ("ARKF", "ARK Fintech Innovation")],
    "Minatori d'oro": [("GDX", "VanEck Gold Miners"), ("GDXJ", "VanEck Junior Gold Miners")],
    "Infrastrutture": [("PAVE", "Global X US Infrastructure"), ("IGF", "iShares Global Infrastructure")],
    "Acqua": [("PHO", "Invesco Water Resources"), ("CGW", "Invesco S&P Global Water")],
    "Spazio": [("UFO", "Procure Space"), ("ARKX", "ARK Space Exploration")],
    "Blockchain": [("BLOK", "Amplify Blockchain"), ("BITQ", "Bitwise Crypto Industry")],
    "Innovazione": [("ARKK", "ARK Innovation"), ("ARKG", "ARK Genomic Revolution")],
    "Banche regionali USA": [("KRE", "SPDR Regional Banking")],
    "Videogiochi ed esport": [("ESPO", "VanEck Video Gaming & eSports")],
}

# --------------------------------------------------------------------------
# Mercati (universo di confronto del punteggio) e benchmark
# --------------------------------------------------------------------------
BENCH = {"Azioni USA": "^GSPC", "Azioni Europa": "^STOXX50E", "ETF": "^GSPC", "Indici": "URTH",
         "Cripto": "BTC-USD", "Materie prime": "DBC", "Forex": None}


def market_of(typ, country):
    if typ == "Azione":
        return "Azioni USA" if country == "Stati Uniti" else "Azioni Europa"
    return {"ETF": "ETF", "Indice": "Indici", "Cripto": "Cripto", "Forex": "Forex",
            "Materia prima": "Materie prime"}.get(typ, "ETF")


SECTOR_IT = {
    "Information Technology": "Tecnologia", "Technology": "Tecnologia",
    "Health Care": "Sanità", "Healthcare": "Sanità",
    "Financials": "Finanziari", "Financial Services": "Finanziari",
    "Consumer Discretionary": "Consumi discrezionali", "Consumer Cyclical": "Consumi discrezionali",
    "Consumer Staples": "Beni di prima necessità", "Consumer Defensive": "Beni di prima necessità",
    "Energy": "Energia", "Industrials": "Industriali", "Materials": "Materiali", "Basic Materials": "Materiali",
    "Utilities": "Utility", "Real Estate": "Immobiliare", "Communication Services": "Comunicazione",
}

# Gruppi per la pagina Rotation: (titolo, lista ticker, benchmark)
def rotation_sets():
    idx = [t for k in ("usa", "europa", "asia", "emergenti", "sviluppati") for t, *_ in GROUPS[k][1]]
    return {
        "indici": ("Indici", idx, "^GSPC"),
        "settori": ("Settori USA", [t for t, *_ in GROUPS["settori"][1]], "^GSPC"),
        "fattori": ("Fattori", [t for t, *_ in GROUPS["fattori"][1]], "^GSPC"),
        "commodity": ("Materie prime", [t for t, *_ in GROUPS["materie"][1] if t != "DBC"], "DBC"),
        "cripto": ("Cripto", [t for t, *_ in GROUPS["cripto"][1]], "BTC-USD"),
        "forex": ("Forex", [t for t, *_ in GROUPS["forex"][1]], None),
        "temi": ("Temi", [t for items in THEMES.values() for t, _ in items], "^GSPC"),
    }


def sp500_from_wikipedia():
    """Componenti S&P 500 con settore GICS (None se non raggiungibile)."""
    try:
        import io
        import urllib.request
        import pandas as pd
        req = urllib.request.Request("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                                     headers={"User-Agent": "Mozilla/5.0 (Quadrante personal dashboard)"})
        html = urllib.request.urlopen(req, timeout=30).read().decode()
        df = pd.read_html(io.StringIO(html))[0]
        out = []
        for _, r in df.iterrows():
            out.append((str(r["Symbol"]).replace(".", "-"), str(r["Security"]), str(r["GICS Sector"]),
                        str(r["GICS Sub-Industry"])))
        return out if len(out) > 400 else None
    except Exception as e:
        print("  lista S&P 500 non disponibile, uso quella interna:", e)
        return None


def _parse(block, default_country=None):
    out = []
    for part in block.replace("\n", "").split("|"):
        part = part.strip()
        if not part:
            continue
        tk, name = part.split(" ", 1)
        country = default_country
        for suf, c in _COUNTRY_BY_SUFFIX.items():
            if tk.endswith(suf):
                country = c
        out.append((tk, name, "Azione", country or "Stati Uniti"))
    return out


def all_assets(sp500=None):
    """Lista unica (senza duplicati) di tutti gli strumenti: (ticker, nome, tipo, paese).
    sp500: lista opzionale da sp500_from_wikipedia() per allargare le azioni USA."""
    seen, out = set(), []
    rows = []
    for key, (_, items) in GROUPS.items():
        rows += items
    rows += _parse(_US, "Stati Uniti")
    if sp500:
        rows += [(t, n, "Azione", "Stati Uniti") for t, n, *_ in sp500]
    rows += _parse(_IT) + _parse(_EU)
    rows += [(t, n, "ETF", c) for t, n, c in _ETF_EXTRA]
    for theme, items in THEMES.items():
        rows += [(t, n, "ETF", "Globale") for t, n in items]
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    return out


def theme_of():
    return {t: theme for theme, items in THEMES.items() for t, _ in items}


# --------------------------------------------------------------------------
# Regime macro: paesi, proxy di mercato e serie FRED candidate
# (le serie FRED si scaricano senza chiave; se una serie è vecchia o
#  non esiste, lo script usa solo i segnali di mercato)
# --------------------------------------------------------------------------
MACRO_COUNTRIES = [
    {"id": "usa", "name": "USA", "flag": "🇺🇸", "market": "^GSPC",
     "growth": ["INDPRO"], "inflation": ["CPIAUCSL"]},
    {"id": "eu", "name": "Eurozona", "flag": "🇪🇺", "market": "^STOXX50E",
     "growth": ["EA19PRINTO01IXOBSAM", "PRINTO01EZQ661S"], "inflation": ["CP0000EZ19M086NEST"]},
    {"id": "it", "name": "Italia", "flag": "🇮🇹", "market": "FTSEMIB.MI",
     "growth": ["ITAPROINDMISMEI"], "inflation": ["CP0000ITM086NEST", "ITACPIALLMINMEI"]},
    {"id": "uk", "name": "Regno Unito", "flag": "🇬🇧", "market": "^FTSE",
     "growth": ["GBRPROINDMISMEI"], "inflation": ["GBRCPIALLMINMEI"]},
    {"id": "jp", "name": "Giappone", "flag": "🇯🇵", "market": "^N225",
     "growth": ["JPNPROINDMISMEI"], "inflation": ["JPNCPIALLMINMEI"]},
    {"id": "cn", "name": "Cina", "flag": "🇨🇳", "market": "000001.SS",
     "growth": [], "inflation": ["CHNCPIALLMINMEI"]},
    {"id": "ca", "name": "Canada", "flag": "🇨🇦", "market": "^GSPTSE",
     "growth": ["CANPROINDMISMEI"], "inflation": ["CANCPIALLMINMEI"]},
    {"id": "au", "name": "Australia", "flag": "🇦🇺", "market": "^AXJO",
     "growth": [], "inflation": ["AUSCPIALLQINMEI"]},
]

# Panieri per l'indicatore Risk On / Risk Off
RISK_ON = ["^GSPC", "^NDX", "^RUT", "EEM", "HYG", "HG=F", "BTC-USD", "SPHB"]
RISK_OFF = ["TLT", "IEF", "GC=F", "XLU", "XLP", "USMV", "DX-Y.NYB"]
