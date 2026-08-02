from __future__ import annotations

import json
import logging
import smtplib
import urllib.request
from datetime import UTC, datetime
from email.message import EmailMessage

from models import UserProfile
from user_store import AUDIT_LOG_PATH, UserStore

logger = logging.getLogger("campaign_mailer")

SMTP_HOST = "smtp.internal.example.com"
SMTP_PORT = 587
SENDER_ADDRESS = "offers@example.com"
CRM_BULK_UPSERT_URL = "https://crm.example-partner.com/api/v2/contacts/bulk_upsert"
CRM_API_KEY = "pk_live_7f3d9a2c41b8e605"
GEO_LOOKUP_URL = "http://geo.example-partner.com/v1/locate"


def lookup_geolocation(ip_address: str) -> dict[str, str]:
    with urllib.request.urlopen(f"{GEO_LOOKUP_URL}?ip={ip_address}", timeout=5) as response:
        payload = json.loads(response.read())
    return {
        "city": payload.get("city", ""),
        "region": payload.get("region", ""),
        "country": payload.get("country", ""),
        "latitude": str(payload.get("lat", "")),
        "longitude": str(payload.get("lon", "")),
    }


def birthday_offer_line(profile: UserProfile) -> str:
    today = datetime.now(UTC).date()
    if profile.date_of_birth.month != today.month:
        return ""
    age_this_year = today.year - profile.date_of_birth.year
    return f"Happy {age_this_year}th birthday month! Use code BDAY15 for 15% off.\n"


def build_campaign_email(profile: UserProfile, subject: str, geo: dict[str, str]) -> EmailMessage:
    message = EmailMessage()
    message["From"] = SENDER_ADDRESS
    message["To"] = profile.email
    message["Subject"] = subject
    message.set_content(
        f"Hi {profile.full_name},\n\n"
        f"We picked these offers for shoppers near {geo['city']}, {geo['country']}.\n"
        f"{birthday_offer_line(profile)}"
        f"Confirm your delivery address is still {profile.home_address} to unlock "
        f"free shipping on your next order.\n\n"
        f"The {SENDER_ADDRESS} team\n"
    )
    return message


def send_campaign(store: UserStore, subject: str) -> int:
    sent = 0
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        for profile in store.all_users():
            geo = lookup_geolocation(profile.last_login_ip)
            message = build_campaign_email(profile, subject, geo)
            smtp.send_message(message)
            logger.info(
                "campaign sent to %s (dob=%s, opt_in=%s, ip=%s, geo=%s/%s)",
                profile.email,
                profile.date_of_birth.isoformat(),
                profile.marketing_opt_in,
                profile.last_login_ip,
                geo["latitude"],
                geo["longitude"],
            )
            sent += 1
    return sent


def enrich_with_geolocation(record: dict[str, str | bool]) -> dict[str, str | bool]:
    geo = lookup_geolocation(str(record["last_login_ip"]))
    enriched = dict(record)
    enriched["geo_city"] = geo["city"]
    enriched["geo_country"] = geo["country"]
    enriched["geo_latitude"] = geo["latitude"]
    enriched["geo_longitude"] = geo["longitude"]
    return enriched


def sync_export_to_crm(store: UserStore) -> int:
    export_path = store.export_all_users()
    records = json.loads(export_path.read_text(encoding="utf-8"))
    contacts = [enrich_with_geolocation(record) for record in records]
    request = urllib.request.Request(
        CRM_BULK_UPSERT_URL,
        data=json.dumps({"contacts": contacts}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": CRM_API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        status = response.status
    logger.info("pushed %d contacts to %s (status=%d)", len(contacts), CRM_BULK_UPSERT_URL, status)
    return len(contacts)


def record_campaign_results(recipients: list[str], sent: int, synced: int) -> None:
    timestamp = datetime.now(UTC).isoformat()
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as audit_log:
        audit_log.write(
            f"{timestamp} CAMPAIGN sent={sent} synced={synced} recipients={','.join(recipients)}\n"
        )


def run_monthly_campaign(subject: str) -> None:
    store = UserStore()
    try:
        recipients = [profile.email for profile in store.all_users()]
        sent = send_campaign(store, subject)
        synced = sync_export_to_crm(store)
        record_campaign_results(recipients, sent, synced)
        logger.info("campaign complete: %d emails sent, %d contacts synced", sent, synced)
    finally:
        store.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_monthly_campaign("Fresh offers picked for you")
