"""Central configuration for LinkedIn Networking Copilot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_PATH = os.getenv("DATABASE_PATH", "database/linkedin.db")

# LLM: ollama | lmstudio
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
LMSTUDIO_HOST = os.getenv("LMSTUDIO_HOST", "http://localhost:1234")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

MY_NAME = os.getenv("MY_NAME", "Your Name")
MY_SCHOOL = os.getenv("MY_SCHOOL", "University at Buffalo")
MY_DEGREE = os.getenv("MY_DEGREE", "MS in Data Science")
MY_TARGET_ROLE = os.getenv("MY_TARGET_ROLE", "internship opportunities")
MY_INTERNSHIP_FIELD = os.getenv("MY_INTERNSHIP_FIELD", "")
MY_LOCATION = os.getenv("MY_LOCATION", "Hyderabad")

# Scoring
MIN_CONTACT_SCORE = int(os.getenv("MIN_CONTACT_SCORE", "50"))
WEEKLY_MESSAGE_LIMIT = int(os.getenv("WEEKLY_MESSAGE_LIMIT", "10"))

# Safety limits — protect your LinkedIn account
MAX_SCRAPE_PER_SESSION = int(os.getenv("MAX_SCRAPE_PER_SESSION", "15"))
MAX_SCRAPE_PER_DAY = int(os.getenv("MAX_SCRAPE_PER_DAY", "25"))
SCRAPE_DELAY_SECONDS = float(os.getenv("SCRAPE_DELAY_SECONDS", "3.0"))

# Manual approval is always required — never change this to True
MANUAL_APPROVAL_REQUIRED = True
AUTO_SEND_ENABLED = False

TARGET_COMPANIES: dict[str, int] = {
    "amazon": 30,
    "microsoft": 30,
    "meta": 30,
    "google": 25,
    "databricks": 25,
    "snowflake": 25,
    "netflix": 20,
    "uber": 20,
}

RECRUITER_BONUS: dict[str, int] = {
    "university_recruiter": 25,
    "campus_recruiter": 25,
    "senior_recruiter": 20,
    "technical_recruiter": 18,
    "talent_acquisition": 15,
    "recruiter": 15,
}

ALUMNI_BONUS: dict[str, int] = {
    "ub_alumni": 30,
    "same_degree": 15,
    "hyderabad": 10,
    "telangana": 8,
}
