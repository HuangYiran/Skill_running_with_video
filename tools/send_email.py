#!/usr/bin/env python3
"""Send a plain text summary email with SMTP settings from environment variables.

Environment variables:
  SMTP_HOST       default: localhost
  SMTP_PORT       default: 25
  SMTP_USER       optional
  SMTP_PASS       optional
  SMTP_FROM       default: noreply@localhost
  SMTP_USE_TLS    default: false
  SMTP_USE_SSL    default: false
  TARGET_EMAIL    optional default recipient
  TARGET_EMAIL_FILE default: config/target_email.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import smtplib
import ssl
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
    parser.add_argument(
        "--allow-fallback-success",
        action="store_true",
        help=(
            "Treat local fallback artifact as success when SMTP delivery fails. "
            "By default, delivery failures exit with code 1."
        ),
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


def build_smtp_info_request(
    *,
    exc: Exception,
    host: str,
    port: int,
    use_tls: bool,
    use_ssl: bool,
    user: str | None,
    has_password: bool,
    from_addr: str | None,
    to_addr: str | None,
) -> str:
    auth_mode = "username+password" if user and has_password else "none-or-incomplete"
    transport = "smtps" if use_ssl else "smtp"
    return "\n".join(
        [
            "Please provide the following information to troubleshoot SMTP failure:",
            f"- Full SMTP error output (current error: {exc!r})",
            f"- SMTP endpoint confirmation: {transport}://{host}:{port}",
            f"- Encryption mode confirmation: SMTP_USE_TLS={use_tls}, SMTP_USE_SSL={use_ssl}",
            f"- Auth mode used by provider: {auth_mode}",
            (
                "- Network check from runtime host: "
                f"`nc -vz {host} {port}` or equivalent connectivity result"
            ),
            (
                "- Provider policy details: app password/OAuth requirement, "
                "allowed sender domain"
            ),
            f"- Envelope info used: FROM={from_addr or ''}, TO={to_addr or ''}",
        ]
    )


def send(msg: EmailMessage) -> tuple[bool, str]:
    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    use_tls = os.getenv("SMTP_USE_TLS", "false").lower() in {"1", "true", "yes"}
    use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes"}

    try:
        smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_cls(host=host, port=port, timeout=15) as server:
            if not use_ssl:
                server.ehlo()
            if use_tls and not use_ssl:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        protocol = "smtps" if use_ssl else "smtp"
        return True, f"Email sent successfully via {protocol}://{host}:{port}"
    except Exception as exc:  # pragma: no cover - operational fallback
        info_request = build_smtp_info_request(
            exc=exc,
            host=host,
            port=port,
            use_tls=use_tls,
            use_ssl=use_ssl,
            user=user,
            has_password=bool(password),
            from_addr=msg.get("From"),
            to_addr=msg.get("To"),
        )
        fallback_dir = pathlib.Path(".email_fallback")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_file = fallback_dir / f"email_{ts}.txt"
        fallback_file.write_text(
            f"Failed to send email: {exc}\n\n"
            f"From: {msg.get('From')}\n"
            f"To: {msg.get('To')}\n"
            f"Subject: {msg.get('Subject')}\n\n"
            f"{info_request}\n\n"
            f"{msg.get_content()}",
            encoding="utf-8",
        )
        return (
            False,
            "SMTP failed. "
            f"{info_request.splitlines()[0]} "
            f"Fallback written to {fallback_file}",
        )


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
        if args.allow_fallback_success:
            raise SystemExit(0)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
