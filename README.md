# Portfolio Watch (analyzer)

Rutina semanal local que lee tu portfolio IOL, analiza posiciones contra
mercado y noticias, y manda un reporte por Telegram. Solo lectura — nunca
emite órdenes ni hace POSTs a IOL.

## Stack

- Python 3.11+
- `requests`, `python-dotenv`, `yfinance`
- Claude Code orquesta el análisis (judgment-based parts)
- Disparado por scheduled-tasks MCP de Claude Code (cron domingo)

## Setup (una vez)

1. **Python**: confirmá `python --version` ≥ 3.11.
2. **Dependencias**:
   ```
   cd C:\Users\Fede\Documents\Arduino\PortfolioMonitor\analyzer
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Credenciales**: copiar `.env.example` a `.env` y completar:
   - `IOL_USER`, `IOL_PASS` — tu cuenta IOL
   - `TELEGRAM_BOT_TOKEN` — obtenido vía @BotFather
   - `TELEGRAM_CHAT_ID` — obtenido vía `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. **Test manual**:
   ```
   python portfolio_fetch.py    # debería imprimir tu portfolio en JSON
   python market_data.py AAPL   # debería traer data de AAPL
   echo "test" | python send_telegram.py   # debería llegarte mensaje
   ```

## Disparo automático

El scheduled-tasks MCP de Claude Code corre el `prompt.md` cada domingo
19:00 ART. La task se crea desde Claude — pedir: *"crear scheduled task
para rutina portfolio"*.

## Archivos

| Archivo | Función |
|---------|---------|
| `portfolio_fetch.py` | Auth IOL + GET portafolio AR/US + GET operaciones |
| `market_data.py` | yfinance: ATH, 52w, MAs, RSI, volumen |
| `send_telegram.py` | POST mensaje al bot |
| `prompt.md` | Instrucciones que ejecuta Claude semanalmente |
| `.env` | Credenciales (gitignored) |
| `output/` | JSONs y reportes históricos (gitignored) |

## Seguridad

- `.env` jamás se commitea (ver `.gitignore`).
- Scripts solo emiten GETs a IOL. Cualquier cambio que introduzca POST/PUT/DELETE rompe la garantía read-only.
- Token IOL vive solo en memoria del proceso (≤30s) y nunca se persiste.
