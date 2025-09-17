# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Chatbot DB
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # Moodle DB
    MOODLE_DB_USER: str
    MOODLE_DB_PASSWORD: str
    MOODLE_DB_HOST: str
    MOODLE_DB_PORT: int
    MOODLE_DB_NAME: str
    TARGET_COURSE_ID: int

    # Twilio
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_FROM_NUMBER: str
    TWILIO_MESSAGING_SERVICE_SID: str | None = None

    WHATSAPP_VERIFY_TOKEN: str

    # --- AÑADE ESTAS TRES LÍNEAS PARA JWT ---
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    TEST_MODE_PHONE_NUMBER: str | None = None
    TEST_PHONE_NUMBER: str | None = None

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()