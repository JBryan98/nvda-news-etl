import logging
import os
import requests
import json

from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve()
load_dotenv(BASE_DIR / ".env")

def get_news(time_from: str, time_to):
    logger.info("Cargando noticias para el rango de tiempo: %s - %s", time_from, time_to)
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": "NVDA",
        "limit": 1000,
        "time_from": time_from,
        "time_to": time_to,
        "apikey": os.getenv("ALPHA_VANTAGE_API_KEY"),
    }
    response = requests.get(url, params=params)
    error_msg = f"Hubo un error al procesar la solicitud para {time_from}__{time_to}"
    if response.status_code == 200:
        json_data = response.json()
        try:
            items = json_data["feed"]
            return items
        except KeyError:
            logger.error(
                f"{error_msg}: Response [{response.status_code}]\n%s",
                json.dumps(json_data, indent=4, ensure_ascii=False)
            )
            return None
    else:
        logger.error(f"{error_msg}: Response [{response.status_code}]")
        return None