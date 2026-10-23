import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class MarketauxApiError(Exception):
    message: str
    http_status: int
    error_code: str
    error_detail: str
    usage_limit: Optional[str] = None
    rate_limit: Optional[str] = None

    def __str__(self):
        parts = [self.message, f"http_status={self.http_status}", f"error_code={self.error_code}"]
        if self.error_detail:
            parts.append(f"error_detail={self.error_detail}")
        if self.usage_limit:
            parts.append(f"usage_limit={self.usage_limit}")
        if self.rate_limit:
            parts.append(f"rate_limit={self.rate_limit}")
        return " | ".join(parts)


def _build_marketaux_params(time_from: str, time_to: str, page: int):
    return {
        "api_token": os.getenv("MARKETAUX_API_TOKEN"),
        "symbols": "NVDA",
        "filter_entities": "true",
        "must_have_entities": "true",
        "group_similar": "false",
        "language": "en",
        "sort": "published_at",
        "published_after": time_from,
        "published_before": time_to,
        "page": page,
    }


def _raise_marketaux_error(response: requests.Response):
    payload = {}
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    error = payload.get("error", {})
    code = error.get("code", "unknown_error")
    detail = error.get("message", response.text)
    usage_limit = response.headers.get("X-UsageLimit-Limit")
    rate_limit = response.headers.get("X-RateLimit-Limit")
    raise MarketauxApiError(
        message="Error al consumir Marketaux",
        http_status=response.status_code,
        error_code=code,
        error_detail=detail,
        usage_limit=usage_limit,
        rate_limit=rate_limit,
    )


def get_news(time_from: str, time_to: str):
    logger.info("Cargando noticias Marketaux para el rango de tiempo: %s - %s", time_from, time_to)
    if not os.getenv("MARKETAUX_API_TOKEN"):
        raise ValueError("MARKETAUX_API_TOKEN no está configurado.")

    url = "https://api.marketaux.com/v1/news/all"
    page = 1
    all_items = []

    while True:
        params = _build_marketaux_params(time_from, time_to, page)
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            _raise_marketaux_error(response)

        payload = response.json()
        meta = payload.get("meta", {})
        items = payload.get("data", [])
        all_items.extend(items)

        returned = meta.get("returned", len(items))
        limit = meta.get("limit", len(items))
        logger.info("Marketaux página %s: returned=%s, limit=%s, acumulado=%s", page, returned, limit, len(all_items))

        if not items or returned < limit:
            break
        # Dormir 1.5 segundos para evitar superar el límite de velocidad de la API
        time.sleep(1.5)
        page += 1

    return all_items