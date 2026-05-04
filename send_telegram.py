"""Send a Telegram message via bot API.

Reads message body from stdin or --text arg. Splits into 4096-char chunks
(Telegram's hard limit) preserving line boundaries when possible.
"""

from __future__ import annotations

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

API = "https://api.telegram.org"
MAX_CHUNK = 4000


def chunk_message(text: str, limit: int = MAX_CHUNK) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def send(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> None:
    for part in chunk_message(text):
        resp = requests.post(
            f"{API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": part, "parse_mode": parse_mode, "disable_web_page_preview": True},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"telegram send failed: HTTP {resp.status_code} body={resp.text[:300]}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in env", file=sys.stderr)
        sys.exit(2)

    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="message text; if omitted, read stdin")
    ap.add_argument("--parse-mode", default="Markdown", choices=["Markdown", "MarkdownV2", "HTML", "None"])
    args = ap.parse_args()

    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        print("empty message, nothing to send", file=sys.stderr)
        sys.exit(2)

    parse_mode = "" if args.parse_mode == "None" else args.parse_mode
    send(token, chat_id, text, parse_mode)


if __name__ == "__main__":
    main()
