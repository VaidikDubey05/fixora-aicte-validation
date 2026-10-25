import re
from typing import Any, Dict, Optional, Set

DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "password",
    "hashed_password",
    "secret",
    "token",
    "access_token",
    "phone",
    "contact_phone",
    "mobile",
    "aadhaar",
    "pan",
    "bank_account",
    "account_number",
    "ssn",
}


def mask_email(email: Optional[str]) -> str:
    """
    Masks email addresses for privacy, e.g.:
    'principal@gecpune.edu.in' -> 'p***l@gecpune.edu.in'
    'ab@domain.com' -> 'a*@domain.com'
    """
    if not email or "@" not in email:
        return "[REDACTED]"
    parts = email.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[0] + "*"
    else:
        masked_user = user[0] + ("*" * (len(user) - 2)) + user[-1]
    return f"{masked_user}@{domain}"


def mask_phone(phone: Optional[str]) -> str:
    """
    Masks phone numbers, preserving only the last 4 digits:
    '+91 9876543210' -> '+91 ******3210'
    '9876543210' -> '******3210'
    """
    if not phone:
        return "[REDACTED]"
    digits_only = re.sub(r"\D", "", phone)
    if len(digits_only) < 4:
        return "****"
    last_four = digits_only[-4:]
    prefix = phone[:-4] if len(phone) > 4 else ""
    return re.sub(r"\d", "*", prefix) + last_four


def mask_aadhaar(aadhaar: Optional[str]) -> str:
    """
    Masks Indian 12-digit Aadhaar number:
    '1234 5678 9012' -> 'XXXX-XXXX-9012'
    """
    if not aadhaar:
        return "[REDACTED]"
    digits = re.sub(r"\D", "", aadhaar)
    if len(digits) < 4:
        return "XXXX-XXXX-XXXX"
    return f"XXXX-XXXX-{digits[-4:]}"


def mask_pan(pan: Optional[str]) -> str:
    """
    Masks Indian 10-character PAN number:
    'ABCDE1234F' -> 'ABCDE****F'
    """
    if not pan or len(pan) != 10:
        return "[REDACTED]"
    return f"{pan[:5]}****{pan[-1]}"


def mask_value_by_key(key: str, value: Any) -> Any:
    """Masks a specific field value based on its key name."""
    if value is None:
        return None

    str_val = str(value)
    lower_key = key.lower()

    if any(k in lower_key for k in ("password", "secret", "token")):
        return "[REDACTED]"
    elif any(k in lower_key for k in ("phone", "mobile")):
        return mask_phone(str_val)
    elif "email" in lower_key:
        return mask_email(str_val)
    elif "aadhaar" in lower_key:
        return mask_aadhaar(str_val)
    elif "pan" in lower_key and len(str_val) == 10:
        return mask_pan(str_val)
    elif any(k in lower_key for k in ("bank", "account_number")):
        digits = re.sub(r"\D", "", str_val)
        return ("*" * max(4, len(digits) - 4)) + (digits[-4:] if len(digits) >= 4 else "****")
    return value


def mask_dict(
    data: Any,
    sensitive_keys: Optional[Set[str]] = None,
) -> Any:
    """
    Recursively redacts or masks sensitive personal data in dictionaries and lists
    prior to serialization in responses or application logs.
    """
    keys_to_mask = sensitive_keys or DEFAULT_SENSITIVE_KEYS

    if isinstance(data, dict):
        masked: Dict[str, Any] = {}
        for k, v in data.items():
            lower_k = k.lower()
            if lower_k in keys_to_mask or any(s in lower_k for s in ("password", "secret", "token")):
                masked[k] = mask_value_by_key(k, v)
            elif any(s in lower_k for s in ("phone", "aadhaar", "pan")):
                masked[k] = mask_value_by_key(k, v)
            elif isinstance(v, (dict, list)):
                masked[k] = mask_dict(v, keys_to_mask)
            else:
                masked[k] = v
        return masked
    elif isinstance(data, list):
        return [mask_dict(item, keys_to_mask) for item in data]
    return data
