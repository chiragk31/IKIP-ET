#!/usr/bin/env python3
"""
Environment Variable Validation Script

Run this script before starting the backend to verify all required
environment variables are configured correctly.

Usage:
    python scripts/check_env.py

Exit codes:
    0 = All required variables are set
    1 = One or more required variables are missing
"""

import os
import sys
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
    else:
        print(f"⚠ No .env file found at {env_path}")
except ImportError:
    print("⚠ python-dotenv not installed. Reading from system environment.")

# Define required variables with descriptions
REQUIRED_BACKEND_VARS = {
    "SUPABASE_URL": "Supabase project URL",
    "SUPABASE_SERVICE_ROLE_KEY": "Supabase service role key",
    "GEMINI_API_KEY": "Google Gemini API key",
    "NEO4J_URI": "Neo4j Aura connection URI",
    "NEO4J_USERNAME": "Neo4j username",
    "NEO4J_PASSWORD": "Neo4j password",
    "PINECONE_API_KEY": "Pinecone API key",
    "PINECONE_INDEX": "Pinecone index name",
    "INNGEST_SIGNING_KEY": "Inngest signing key",
    "INNGEST_EVENT_KEY": "Inngest event key",
}

OPTIONAL_VARS = {
    "SUPABASE_ANON_KEY": "Supabase anonymous key (for frontend)",
    "GEMINI_MODEL": "Gemini model name (default: gemini-2.5-flash)",
    "PINECONE_ENVIRONMENT": "Pinecone environment (default: us-east-1-aws)",
    "APP_ENV": "Application environment (default: development)",
    "LOG_LEVEL": "Log level (default: INFO)",
}


def check_variables():
    """Check all required environment variables."""
    print("\n" + "="*60)
    print("Industrial Knowledge Intelligence Platform")
    print("Environment Variable Validation")
    print("="*60 + "\n")

    missing = []
    present = []

    # Check required variables
    print("REQUIRED VARIABLES:")
    print("-" * 40)
    for var, description in REQUIRED_BACKEND_VARS.items():
        value = os.environ.get(var)
        if not value:
            missing.append(var)
            print(f"  ✗ {var:40s} — MISSING ({description})")
        else:
            # Mask sensitive values
            display = value[:8] + "..." if len(value) > 8 else value
            present.append(var)
            print(f"  ✓ {var:40s} — {display}")

    print("\nOPTIONAL VARIABLES:")
    print("-" * 40)
    for var, description in OPTIONAL_VARS.items():
        value = os.environ.get(var)
        if value:
            print(f"  ✓ {var:40s} — Set")
        else:
            print(f"  ~ {var:40s} — Not set (using default) ({description})")

    print("\n" + "="*60)
    print(f"Results: {len(present)}/{len(REQUIRED_BACKEND_VARS)} required variables configured")

    if missing:
        print(f"\n❌ FAILED: {len(missing)} required variable(s) missing:")
        for var in missing:
            print(f"   - {var}: {REQUIRED_BACKEND_VARS[var]}")
        print("\nPlease copy backend/.env.example to backend/.env and fill in all values.")
        sys.exit(1)
    else:
        print("\n✅ All required environment variables are configured.")
        print("The backend should start successfully.")
        sys.exit(0)


if __name__ == "__main__":
    check_variables()
