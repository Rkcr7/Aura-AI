import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import dotenv_values

class Settings(BaseSettings):
    """
    Manages application settings and loads them from a .env file.
    All defaults should be production-safe values that match .env file settings.
    """
    # Required API Keys (no defaults - must be provided)
    DEEPGRAM_API_KEY: str

    # Optional API Keys (default empty so the app still starts if unset)
    # 60db is a selectable alternative speech-to-text engine alongside Deepgram.
    SIXTYDB_API_KEY: str = ""

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    # Development Mode - Controls debugging features
    # Default to False for production safety, .env file controls actual value
    DEV_MODE: bool = False
    
    # AI Configuration - Defaults match .env file values
    TRACK_CANDIDATE_RESPONSES: bool = True
    INCLUDE_CONVERSATION_HISTORY: bool = True
    MAX_CONVERSATION_HISTORY: int = 6
    GENERATE_FULL_ANSWERS: bool = True
    PERSONALIZE_ANSWERS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'  # <-- This is the simple fix. It tells Pydantic to ignore unknown env vars.
    )

# --- Manual Override for .env Priority ---
# Load settings from .env file first
env_settings = Settings(_env_file=".env", _env_file_encoding='utf-8')

# Now create the final settings instance.
# By passing `env_settings` as keyword arguments, we force its values to take
# priority over any system environment variables that Pydantic would otherwise load.
settings = Settings(**env_settings.model_dump())


def print_config_debug():
    """Debug function to show current configuration values and their sources"""
    print("🔧 CONFIGURATION DEBUG:")
    
    # --- DEV_MODE Debugging ---
    raw_dev_mode_os = os.getenv('DEV_MODE', 'Not Set')
    env_file_vals = dotenv_values(".env")
    dev_mode_in_file = env_file_vals.get('DEV_MODE', 'Not found in .env')

    if raw_dev_mode_os != 'Not Set' and raw_dev_mode_os.lower() != str(settings.DEV_MODE).lower():
        print("   ⚠️  WARNING: Environment variable conflict detected!")
        print(f"      - System environment sets DEV_MODE='{raw_dev_mode_os}'")
        print(f"      - .env file sets DEV_MODE='{dev_mode_in_file}'")
        print(f"      - ✅ Using value from .env file: {settings.DEV_MODE}")

    print(f"\n   --- Final Values ---")
    print(f"   ⚙️ DEV_MODE (Final Value Used) = {settings.DEV_MODE}")
    
    # --- Other Settings ---
    print(f"   📊 LOG_LEVEL = {settings.LOG_LEVEL}")
    print(f"   🤖 AI Settings:")
    print(f"      TRACK_CANDIDATE_RESPONSES = {settings.TRACK_CANDIDATE_RESPONSES}")
    print(f"      INCLUDE_CONVERSATION_HISTORY = {settings.INCLUDE_CONVERSATION_HISTORY}")
    print(f"      MAX_CONVERSATION_HISTORY = {settings.MAX_CONVERSATION_HISTORY}")
    print(f"      GENERATE_FULL_ANSWERS = {settings.GENERATE_FULL_ANSWERS}")
    print(f"      PERSONALIZE_ANSWERS = {settings.PERSONALIZE_ANSWERS}")
    print(f"   🔑 API Keys: DEEPGRAM={'*' * 20 if settings.DEEPGRAM_API_KEY else 'Not Set'}")
    print(f"   🔑 API Keys: 60DB={'*' * 20 if settings.SIXTYDB_API_KEY else 'Not Set'}")