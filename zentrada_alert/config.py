"""Configuration loaded from environment variables (.env supported)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# --- Zentrada site ---
ZENTRADA_BASE_URL = os.environ.get("ZENTRADA_BASE_URL", "https://www.zentrada.com")
ZENTRADA_LOGIN_PATH = os.environ.get("ZENTRADA_LOGIN_PATH", "/login")
ZENTRADA_RECOMMENDATIONS_PATH = os.environ.get(
    "ZENTRADA_RECOMMENDATIONS_PATH", "/my/recommendations"
)
ZENTRADA_USERNAME = os.environ.get("ZENTRADA_USERNAME", "")
ZENTRADA_PASSWORD = os.environ.get("ZENTRADA_PASSWORD", "")

# Login form field names. Zentrada requires an authenticated session before the
# recommendation/bestseller pages become available; inspect the real login form
# (browser devtools -> Network -> the POST request) and adjust these to match.
LOGIN_FORM_USERNAME_FIELD = os.environ.get("LOGIN_FORM_USERNAME_FIELD", "username")
LOGIN_FORM_PASSWORD_FIELD = os.environ.get("LOGIN_FORM_PASSWORD_FIELD", "password")

# CSS selectors for the recommendation/product-listing page. These are
# placeholders — open the real page while logged in and update them to match
# the actual markup (browser devtools -> Inspect on one product card).
SELECTOR_PRODUCT_CARD = os.environ.get("SELECTOR_PRODUCT_CARD", ".product-card")
SELECTOR_PRODUCT_NAME = os.environ.get("SELECTOR_PRODUCT_NAME", ".product-name")
SELECTOR_PRODUCT_PRICE = os.environ.get("SELECTOR_PRODUCT_PRICE", ".product-price")
SELECTOR_PRODUCT_LINK = os.environ.get("SELECTOR_PRODUCT_LINK", "a.product-link")
SELECTOR_PRODUCT_SKU = os.environ.get("SELECTOR_PRODUCT_SKU", "")  # optional

# --- Filtering ---
# Comma-separated keywords. An item is treated as an "expected purchase item"
# (구매예상 품목) if its name contains any of these (case-insensitive).
# Leave empty to alert on every recommended item found.
WATCH_KEYWORDS = [
    k.strip()
    for k in os.environ.get("WATCH_KEYWORDS", "").split(",")
    if k.strip()
]

# --- Email (Gmail) ---
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_TO", EMAIL_ADDRESS)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))

# --- Misc ---
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "20"))
DRY_RUN = _get_bool("DRY_RUN", False)
