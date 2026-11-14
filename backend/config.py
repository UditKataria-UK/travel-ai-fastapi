
import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# OMNIROUTE CONFIGURATION
# ==========================================

OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY")

OMNIROUTE_BASE_URL = os.getenv(
    "OMNIROUTE_BASE_URL",
    "http://localhost:20128/v1"
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "groq/openai/gpt-oss-120b"
)


# ==========================================
# EXTERNAL API CONFIGURATION
# ==========================================

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

WEATHER_API_URL = os.getenv(
    "WEATHER_API_URL",
    "https://open-meteo-proxy.katariaudit2005.workers.dev/"
)


# ==========================================
# CORS CONFIGURATION
# ==========================================

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500"
).split(",")


# ==========================================
# SETTINGS VALIDATION
# ==========================================

def validate_settings():
    required_settings = {
        "OMNIROUTE_API_KEY": OMNIROUTE_API_KEY,
        "SERPAPI_API_KEY": SERPAPI_API_KEY,
        "MODEL_NAME": MODEL_NAME,
        "OMNIROUTE_BASE_URL": OMNIROUTE_BASE_URL,
    }

    missing_settings = [
        name for name, value in required_settings.items()
        if not value
    ]

    if missing_settings:
        raise ValueError(
            f"Missing environment variables: {', '.join(missing_settings)}"
        )
