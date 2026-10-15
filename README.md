# Quadrante

Dashboard quantitativa personale, statica, pubblicata su **GitHub Pages** e ricalcolata ogni giorno da una **GitHub Action** gratuita.

## Pagine

| Pagina | Contenuto |
|---|---|
| **Dashboard** | regime economico di 8 aree, sentiment, risk on/off, proposte del giorno, watchlist, panoramica mercati |
| **Portafogli** | i tuoi portafogli (salvati nel browser) con valore, G/P e punteggio; portafogli modello (regola 80/60, top 10%, mercato) con backtest |
| **Radar** | finestre stagionali imminenti, ingressi/uscite della regola 80/60, combinazione delle due |
| **Classifiche** | classifica filtrabile · mappa dei punteggi (treemap per settore) · confronto fino a 4 strumenti |
| **Rotation** | grafico di rotazione relativa (stile RRG) per indici, settori, fattori, materie prime, cripto, forex, temi |
| **Paesi** | indici per regione con regime macro |
| **Temi** | ETF tematici raggruppati, punteggio medio e performance |
| **News e Macro** | trimestrali in arrivo, calendario macro della settimana, Commitment of Traders (CFTC) |
| **Scheda strumento** | punteggio, 5 pilastri con contributi, vantaggio atteso, storico punteggio, evidenza storica della regola, stagionalità, concorrenti |
| **Metodo** | spiegazione del modello e verifica fuori campione |

## Il punteggio (0–100)

È ricostruito sull'impostazione che Quantaste descrive pubblicamente per lo Smart Quant, con calcoli propri:

1. **Cinque pilastri** ogni settimana, ognuno trasformato in percentile dentro il proprio mercato
   (azioni USA, azioni Europa, ETF, indici, cripto, forex, materie prime):
   - **Macro**: extra-rendimento storico dello strumento nelle fasi passate con lo stesso regime USA di oggi (produzione industriale e inflazione da FRED);
   - **Tendenza**: distanza dalla media a 200 giorni e rendimento 12 mesi meno l'ultimo, divisi per la volatilità;
   - **Momentum**: rendimenti 1 e 3 mesi corretti per la volatilità + accelerazione;
   - **Stagionalità**: rendimento medio dei 3 mesi successivi negli stessi giorni degli ultimi 15 anni;
   - **Rischio**: volatilità rispetto alla mediana del mercato.
2. **Obiettivo**: extra-rendimento a 3 mesi rispetto alla mediana del proprio mercato.
3. **Contributi**: regressione ridge sui decili dei pilastri, **rifatta ogni anno usando solo il passato** (nessun dato futuro).
4. **Vantaggio atteso** = somma dei contributi (media mobile di 4 settimane). **Punteggio** = posizione in classifica nel mercato.
5. **Fasce**: 90+ STRONG BUY · 80–89 BUY · 60–79 HOLD · 30–59 SELL · <30 STRONG SELL.
   **Regola**: entra a 80+, esci sotto 60.

Il codice è in `scripts/model.py`. I pesi esatti di Quantaste non sono pubblici: i punteggi saranno simili per logica ma non identici.

### Taratura automatica (`scripts/tune.py`)

L'Action **Taratura del modello** (avvio manuale) prova le varianti del modello sui rendimenti reali:
numero di fasce, regolarizzazione, smussatura del punteggio e esclusione di ciascun pilastro.
Per ogni variante misura l'IC (correlazione di rango tra punteggio ed extra-rendimento a 3 mesi),
lo spread tra punteggi 80+ e sotto 30 e il turnover. Sceglie sul periodo fino a 3 anni fa e controlla
che la variante regga anche sugli ultimi 3 anni (mai usati nella scelta). Il risultato va in
`scripts/model_config.json`, viene salvato nel repository e il sito si ripubblica da solo.
La tabella completa è nella pagina **Metodo**. Conviene rilanciarla ogni qualche mese.

## Universo (~4.000 strumenti)

Ricostruito ogni settimana da fonti pubbliche (`scripts/universe_builder.py`):
S&P 500/400/600 e Nasdaq-100, DAX/MDAX/SDAX, FTSE 100/250, CAC 40/SBF 120, FTSE MIB e Mid Cap, IBEX 35,
AEX/AMX, BEL 20, SMI, OMX Stoccolma/Helsinki/Copenaghen, PSI, ATX, OBX (da Wikipedia); i 1.200 ETF USA più
liquidi (elenco NASDAQ Trader); 40 cripto; indici, forex, materie prime e temi da `scripts/universe.py`.
I prezzi sono in un archivio incrementale (`cache/prices.parquet`, nella cache delle Actions):
la prima esecuzione scarica ~20 anni per tutto (30–60 minuti), le successive solo gli ultimi giorni.

> Nei **dati dimostrativi** i backtest sembrano eccezionali perché i prezzi simulati hanno trend artificialmente persistenti.
> Con i dati reali aspettati risultati molto più modesti: controlla la pagina **Metodo** per la verifica fuori campione.

## Pubblicarlo su GitHub (una volta sola)

1. Crea un repository **pubblico** (es. `quadrante`) e carica tutto il contenuto della cartella, **compresa `.github`**.
   ```bash
   git init && git add . && git commit -m "Prima versione"
   git branch -M main
   git remote add origin https://github.com/<tuo-utente>/quadrante.git
   git push -u origin main
   ```
   > Se carichi dal browser e la cartella `.github` non viene presa, crea a mano il file
   > `.github/workflows/update.yml` (*Add file → Create new file*) e incolla il contenuto.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Prova veloce (consigliata):** tab **Actions → Prova veloce → Run workflow** (5–10 minuti). Prende pochi titoli da
   ogni fonte e stampa nel log una tabella `FONTE / TITOLI / CON PREZZI`: le righe con `!!` indicano una fonte che non
   ha funzionato (es. ticker di una borsa scritti male). Se è tutto `OK`, passa al punto successivo.
4. Tab **Actions** → *Aggiorna dati e pubblica* → **Run workflow**. La prima esecuzione richiede 30–60 minuti
   (scarica ~20 anni di prezzi per ~4.000 strumenti e stima il modello). L'indirizzo del sito compare nel riepilogo dell'esecuzione.
5. Quando la prima esecuzione è finita: **Actions → Taratura del modello → Run workflow** (1–3 ore).
6. Settori e capitalizzazioni delle azioni europee arrivano a blocchi di 400 per esecuzione: dopo una settimana circa sono completi.

Poi si aggiorna da sola dal lunedì al venerdì alle 22:20 UTC e il sabato mattina. I dati non vengono salvati nel repository
(sono pubblicati direttamente su Pages), quindi il repository resta leggero.

### Se il primo download si interrompe

L'archivio prezzi viene salvato ogni ~500 ticker e conservato anche se l'esecuzione fallisce. Ogni esecuzione
scarica al massimo per 100 minuti (`MAX_DOWNLOAD_MIN` nel workflow): se Yahoo rallenta, il resto viene completato
alle esecuzioni successive e intanto il sito usa i dati già presenti. Basta rilanciare l'Action.

## Dettagli utili

- **Strumenti fermi:** se un titolo non ha nuove quotazioni da più di 10 giorni (sospeso, delistato) viene marcato
  `FERMO`, perde il punteggio ed è escluso da proposte, radar e sentiment.
- **Valute:** ogni strumento ha la sua valuta (i titoli di Londra sono in pence, GBp). Nei portafogli valori e totali
  sono convertiti in euro al cambio del giorno; il prezzo di carico va inserito nella valuta dello strumento.
- **Backup:** portafogli e watchlist sono salvati nel browser. In *Portafogli* ci sono **Esporta backup** e
  **Importa backup** per spostarli su un altro computer o sul telefono.

## Provare in locale

```bash
pip install -r scripts/requirements.txt
python scripts/update_data.py --demo        # dati simulati, ~320 strumenti
python scripts/update_data.py --demo-full   # dati simulati, ~3.600 strumenti (test di velocità)
python scripts/tune.py --demo               # prova la taratura sui dati simulati
python scripts/update_data.py          # dati reali
python -m http.server 8000             # poi apri http://localhost:8000
```

## Personalizzare

- **Strumenti**: `scripts/universe.py` (ticker Yahoo Finance). L'S&P 500 completo viene letto da Wikipedia a ogni esecuzione.
- **Temi**: dizionario `THEMES` in `scripts/universe.py`.
- **Soglie e orizzonte**: `ENTRY`, `EXIT`, `H` in `scripts/model.py`.

## Fonti dati

Yahoo Finance (tramite yfinance, uso personale) · FRED – Federal Reserve Bank of St. Louis · CFTC Public Reporting · calendario settimanale ForexFactory · Wikipedia (componenti S&P 500).
Grafici: TradingView Lightweight Charts (Apache 2.0, in `assets/vendor`).

---
Strumento personale di studio. I punteggi sono meccanici, i risultati storici sono backtest: **non è consulenza finanziaria**.
