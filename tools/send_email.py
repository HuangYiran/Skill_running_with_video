#!/usr/bin/env python3
"""Send a plain text summary email with SMTP settings from environment variables.

Environment variables:
  SMTP_HOST       default: localhost
  SMTP_PORT       default: 25
  SMTP_USER       optional
  SMTP_PASS       optional
  SMTP_FROM       default: noreply@localhost
  SMTP_USE_TLS    default: false
  TARGET_EMAIL    optional default recipient
  TARGET_EMAIL_FILE default: config/target_email.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import smtplib
from email.message import EmailMessage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send summary email via SMTP")
    parser.add_argument("--to", required=False, help="Recipient email address")
    parser.add_argument(
        "--to-file",
        default=os.getenv("TARGET_EMAIL_FILE", "config/target_email.txt"),
        help="Path to default recipient email file when --to is omitted",
    )
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument(
        "--body-file",
        required=True,
        help="Path to a text file that contains email body content",
    )
    return parser.parse_args()


def load_body(body_file: str) -> str:
    path = pathlib.Path(body_file).resolve()
    return path.read_text(encoding="utf-8")


def resolve_recipient(to_addr: str | None, to_file: str) -> str | None:
    if to_addr and to_addr.strip():
        return to_addr.strip()

    env_to = os.getenv("TARGET_EMAIL")
    if env_to and env_to.strip():
        return env_to.strip()

    path = pathlib.Path(to_file).resolve()
    if not path.exists():
        return None

    default_to = path.read_text(encoding="utf-8").strip()
    if not default_to:
        return None
    return default_to


def build_message(to_addr: str, subject: str, body: str) -> EmailMessage:
    from_addr = os.getenv("SMTP_FROM", "noreply@localhost")
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def send(msg: EmailMessage) -> tuple[bool, str]:
    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    use_tls = os.getenv("SMTP_USE_TLS", "false").lower() in {"1", "true", "yes"}

    try:
        with smtplib.SMTP(host=host, port=port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        return True, f"Email sent successfully via {host}:{port}"
    except Exception as exc:  # pragma: no cover - operational fallback
        fallback_dir = pathlib.Path(".email_fallback")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_file = fallback_dir / f"email_{ts}.txt"
        fallback_file.write_text(
            f"Failed to send email: {exc}\n\n"
            f"From: {msg.get('From')}\n"
            f"To: {msg.get('To')}\n"
            f"Subject: {msg.get('Subject')}\n\n"
            f"{msg.get_content()}",
            encoding="utf-8",
        )
        return False, f"SMTP failed, fallback written to {fallback_file}"


def main() -> None:
    args = parse_args()
    recipient = resolve_recipient(args.to, args.to_file)
    if not recipient:
        raise SystemExit(
            "Recipient is required: pass --to, set TARGET_EMAIL, or provide TARGET_EMAIL_FILE"
        )
    body = load_body(args.body_file)
    msg = build_message(recipient, args.subject, body)
    ok, message = send(msg)
    print(message)
    if not ok:
        # Fallback artifact is already written for manual relay.
        raise SystemExit(0)


if __name__ == "__main__":
    main()
