"""Fetch IOL portfolio + buy history. Read-only.

Outputs JSON to stdout combining positions across argentina + estados_unidos
plus first/last buy dates per symbol. Refuses to issue any non-GET request.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from dotenv import load_dotenv

API_BASE = "https://api.invertironline.com"
TIMEOUT = 30
HISTORY_YEARS = 10

MONEDA_MAP = {
    "peso_Argentino": "ARS",
    "dolar_Estadounidense": "USD",
}

PAISES = ["argentina", "estados_unidos"]


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def get_token(user: str, password: str) -> str:
    resp = requests.post(
        f"{API_BASE}/token",
        data={"username": user, "password": password, "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        die(f"auth failed: HTTP {resp.status_code} body={resp.text[:200]}")
    return resp.json()["access_token"]


def auth_get(token: str, path: str) -> Any:
    resp = requests.get(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        die(f"GET {path} failed: HTTP {resp.status_code} body={resp.text[:200]}")
    return resp.json()


def normalize_currency(raw: str | None) -> str:
    if not raw:
        return ""
    return MONEDA_MAP.get(raw, raw)


def extract_array(payload: Any, key: str) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload[key]
    return []


def fetch_portfolio(token: str, pais: str) -> list[dict]:
    payload = auth_get(token, f"/api/v2/portafolio/{pais}")
    items = extract_array(payload, "activos")
    out = []
    for it in items:
        titulo = it.get("titulo") or {}
        sym = titulo.get("simbolo") or ""
        if not sym:
            continue
        out.append({
            "symbol": sym,
            "description": titulo.get("descripcion") or "",
            "market": titulo.get("mercado") or "",
            "instrument_type": titulo.get("tipo") or "",
            "currency": normalize_currency(titulo.get("moneda")),
            "country": pais,
            "quantity": float(it.get("cantidad") or 0),
            "ppc": float(it.get("ppc") or 0),
            "last_price": float(it.get("ultimoPrecio") or 0),
            "daily_var_pct": float(it.get("variacionDiaria") or 0),
            "pnl_pct": float(it.get("gananciaPorcentaje") or 0),
            "pnl_abs": float(it.get("gananciaTotal") or 0),
            "valorized": float(it.get("valorizado") or 0),
        })
    return out


def fetch_operaciones(token: str) -> list[dict]:
    fecha_desde = (datetime.now(timezone.utc) - timedelta(days=365 * HISTORY_YEARS)).strftime("%Y-%m-%d")
    payload = auth_get(
        token,
        f"/api/v2/operaciones?filtro.estado=terminadas&filtro.fechaDesde={fecha_desde}",
    )
    return extract_array(payload, "operaciones")


def buy_dates_per_symbol(operaciones: list[dict]) -> dict[str, dict]:
    by_sym: dict[str, dict] = {}
    for op in operaciones:
        sym = (op.get("simbolo") or (op.get("titulo") or {}).get("simbolo") or "").upper()
        if not sym:
            continue
        tipo_raw = op.get("tipo")
        if isinstance(tipo_raw, dict):
            tipo = (tipo_raw.get("descripcion") or "").lower()
        else:
            tipo = str(tipo_raw or "").lower()
        if "compra" not in tipo:
            continue
        date_str = op.get("fechaOperada") or op.get("fechaOrden") or op.get("fecha")
        if not date_str:
            continue
        date = date_str[:10]
        entry = by_sym.setdefault(sym, {"first_buy": date, "last_buy": date, "count": 0})
        if date < entry["first_buy"]:
            entry["first_buy"] = date
        if date > entry["last_buy"]:
            entry["last_buy"] = date
        entry["count"] += 1
    return by_sym


def main() -> None:
    load_dotenv()
    user = os.getenv("IOL_USER")
    password = os.getenv("IOL_PASS")
    if not user or not password:
        die("missing IOL_USER or IOL_PASS in env")

    token = get_token(user, password)

    positions: list[dict] = []
    for pais in PAISES:
        positions.extend(fetch_portfolio(token, pais))

    buy_history = buy_dates_per_symbol(fetch_operaciones(token))
    for p in positions:
        bh = buy_history.get(p["symbol"].upper())
        if bh:
            p["first_buy_date"] = bh["first_buy"]
            p["last_buy_date"] = bh["last_buy"]
            p["buy_operations_count"] = bh["count"]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "positions": positions,
        "summary": {
            "total_positions": len(positions),
            "total_valorized_ars": sum(p["valorized"] for p in positions if p["currency"] == "ARS"),
            "total_valorized_usd": sum(p["valorized"] for p in positions if p["currency"] == "USD"),
        },
    }
    json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
