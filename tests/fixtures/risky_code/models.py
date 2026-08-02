from __future__ import annotations

from dataclasses import dataclass
from datetime import date

EXPORT_FIELDS: tuple[str, ...] = (
    "full_name",
    "email",
    "date_of_birth",
    "home_address",
    "national_id",
    "marketing_opt_in",
    "last_login_ip",
)


@dataclass
class UserProfile:
    full_name: str
    email: str
    date_of_birth: date
    home_address: str
    national_id: str
    marketing_opt_in: bool
    last_login_ip: str

    def to_export_record(self) -> dict[str, str | bool]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "date_of_birth": self.date_of_birth.isoformat(),
            "home_address": self.home_address,
            "national_id": self.national_id,
            "marketing_opt_in": self.marketing_opt_in,
            "last_login_ip": self.last_login_ip,
        }

    def audit_line(self) -> str:
        return (
            f"{self.full_name} <{self.email}> national_id={self.national_id} "
            f"dob={self.date_of_birth.isoformat()} address={self.home_address}"
        )
