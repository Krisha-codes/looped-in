import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import json

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

load_dotenv()

BASE = Path(__file__).parent


def render_email(briefing):
    env = Environment(
        loader=FileSystemLoader(BASE / "templates"),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("email.html").render(**briefing)


def plain_text(b):
    """Simple fallback for email apps that don't show HTML."""
    lines = [f"Looped In - {b['date']}", ""]
    if b.get("headline_story"):
        s = b["headline_story"]
        lines += [s["title"], s["url"], ""]
    for section in b.get("sections", []):
        lines.append(section["name"].upper())
        for s in section["stories"]:
            lines += [s["title"], s["url"]]
        lines.append("")
    return "\n".join(lines)


def send_briefing(briefing):
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_APP_PASSWORD")
    recipients = [r.strip() for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r.strip()]

    if not (sender and password and recipients):
        print("Email not configured in .env, skipping.")
        return

    html = render_email(briefing)
    text = plain_text(briefing)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        # One email per person, so nobody sees anyone else's address
        for to in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Looped In: {briefing['date']}"
            msg["From"] = f"Looped In <{sender}>"
            msg["To"] = to
            msg.attach(MIMEText(text, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))
            server.sendmail(sender, to, msg.as_string())
            print(f"Sent to {to}")


if __name__ == "__main__":
    # Test mode: sends the latest saved briefing, no Gemini request needed
    source = BASE / "briefing.json"
    if not source.exists():
        source = BASE / "sample_briefing.json"
    with open(source, encoding="utf-8") as f:
        send_briefing(json.load(f))