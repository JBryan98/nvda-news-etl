import logging
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# 1. Cargar el archivo .env con el perfil
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
# 2. Obtener el perfil
APP_PROFILE = os.getenv("APP_PROFILE")
# 3. Cargar el archivo .env correspondiente al perfil
load_dotenv(BASE_DIR / f".env.{APP_PROFILE}", override=True)

logger = logging.getLogger(__name__)

def get_connection():
    try:
        logger.info("Conectando con PostgreSQL...")
        connection = psycopg2.connect(
            database = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASSWORD"),
            host = os.getenv("DB_HOST"),
            port = os.getenv("DB_PORT"),
            sslmode = os.getenv("DB_SSL"),
        )
        return connection
    except Exception as e:
        logger.error("Error al conectar a PostgreSQL con psycopg2: %s", e)
        raise