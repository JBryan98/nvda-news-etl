import logging
from datetime import datetime
from decimal import Decimal

from marketaux_api import get_news
from news_repository import get_all_topics, save_news_with_topics

logger = logging.getLogger(__name__)


def map_sentiment_label(score: Decimal):
    if score <= Decimal("-0.35"):
        return "Bearish"
    if score <= Decimal("-0.10"):
        return "Somewhat-Bearish"
    if score < Decimal("0.10"):
        return "Neutral"
    if score < Decimal("0.35"):
        return "Somewhat-Bullish"
    return "Bullish"


def normalize_match_score(match_score):
    numeric = Decimal(str(match_score))
    normalized = numeric / Decimal("100")
    if normalized < Decimal("0"):
        return Decimal("0")
    if normalized > Decimal("1"):
        return Decimal("1")
    return normalized


def to_datetime_utc(published_at: str):
    return datetime.fromisoformat(published_at.replace("Z", "+00:00"))


def compute_overall_sentiment(entities):
    weighted_total = Decimal("0")
    total_weight = Decimal("0")
    for entity in entities:
        sentiment = entity.get("sentiment_score")
        match_score = entity.get("match_score")
        if sentiment is None or match_score is None:
            continue
        weight = normalize_match_score(match_score)
        weighted_total += Decimal(str(sentiment)) * weight
        total_weight += weight
    if total_weight == 0:
        return Decimal("0")
    return weighted_total / total_weight


def build_news_topics(item, valid_topic_codes):
    topics = []
    text = " ".join(
        filter(
            None,
            [
                item.get("title"),
                item.get("description"),
                item.get("snippet"),
                item.get("keywords"),
            ],
        )
    ).lower()

    industry_mapping = {
        "technology": "technology",
        "financial services": "finance",
        "financial": "finance",
        "services": "finance",
        "real estate": "real_estate",
        "healthcare": "life_sciences",
        "consumer cyclical": "retail_wholesale",
        "consumer defensive": "retail_wholesale",
        "consumer goods": "retail_wholesale",
        "industrial goods": "manufacturing",
        "industrials": "manufacturing",
    }
    keyword_mapping = {
        "blockchain": "blockchain",
        "crypto": "blockchain",
        "bitcoin": "blockchain",
        "earnings": "earnings",
        "quarterly results": "earnings",
        "guidance": "earnings",
        "ipo": "ipo",
        "listing": "ipo",
        "merger": "mergers_and_acquisitions",
        "acquisition": "mergers_and_acquisitions",
        "takeover": "mergers_and_acquisitions",
        "market recap": "financial_markets",
        "stock market": "financial_markets",
        "federal reserve": "economy_monetary",
        "interest rates": "economy_monetary",
        "inflation": "economy_macro",
        "gdp": "economy_macro",
        "fiscal": "economy_fiscal",
        "budget": "economy_fiscal",
        "energy": "energy_transportation",
        "transportation": "energy_transportation",
    }

    scored_topics = {}
    for entity in item.get("entities", []):
        industry = (entity.get("industry") or "").strip().lower()
        topic_code = industry_mapping.get(industry)
        if topic_code and topic_code in valid_topic_codes:
            current = scored_topics.get(topic_code, Decimal("0"))
            scored_topics[topic_code] = max(current, Decimal("0.6"))

        entity_type = (entity.get("type") or "").strip().lower()
        if entity_type in ("etf", "mutualfund", "index") and "financial_markets" in valid_topic_codes:
            current = scored_topics.get("financial_markets", Decimal("0"))
            scored_topics["financial_markets"] = max(current, Decimal("0.5"))
        if entity_type == "cryptocurrency" and "blockchain" in valid_topic_codes:
            current = scored_topics.get("blockchain", Decimal("0"))
            scored_topics["blockchain"] = max(current, Decimal("0.6"))

    for token, topic_code in keyword_mapping.items():
        if token in text and topic_code in valid_topic_codes:
            current = scored_topics.get(topic_code, Decimal("0"))
            scored_topics[topic_code] = max(current, Decimal("0.7"))

    for topic_code, score in scored_topics.items():
        if score >= Decimal("0.35"):
            topics.append(
                {
                    "url": item["url"],
                    "topic_code": topic_code,
                    "relevance_score": score,
                }
            )
    return topics


def news_etl(connection, time_from: str, time_to: str):
    logger.info("Iniciando proceso ETL de noticias de Marketaux")
    data = get_news(time_from, time_to)
    if len(data) == 0:
        logger.warning("No se encontraron noticias para el rango de tiempo: %s - %s", time_from, time_to)
        return 0

    logger.info("Procesando datos de noticias de Marketaux")
    data.sort(key=lambda i: i["published_at"])

    db_topics = get_all_topics(connection)
    valid_topic_codes = {topic["code"] for topic in db_topics}

    news_to_insert = []
    news_topics_to_insert = []

    for item in data:
        entities = item.get("entities", [])
        nvda_entity = None
        for entity in entities:
            if entity.get("symbol") == "NVDA":
                nvda_entity = entity
                break

        if nvda_entity is None:
            continue

        relevance_score = normalize_match_score(nvda_entity.get("match_score", 0))
        sentiment_score = Decimal(str(nvda_entity.get("sentiment_score", 0)))
        overall_sentiment_score = compute_overall_sentiment(entities)

        news_to_insert.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "time_published": to_datetime_utc(item.get("published_at")),
                "authors": None,
                "summary": item.get("description") or item.get("snippet"),
                "banner_image": item.get("image_url"),
                "source": item.get("source"),
                "category_within_source": "General",
                "source_domain": item.get("source"),
                "overall_sentiment_score": overall_sentiment_score,
                "overall_sentiment_label": map_sentiment_label(overall_sentiment_score),
                "relevance_score": relevance_score,
                "sentiment_score": sentiment_score,
                "sentiment_label": map_sentiment_label(sentiment_score),
            }
        )
        news_topics_to_insert.extend(build_news_topics(item, valid_topic_codes))

    logger.info("Cargando %s noticias en la base de datos", len(news_to_insert))
    total_news_inserted = save_news_with_topics(connection, news_to_insert, news_topics_to_insert)
    logger.info("Proceso ETL de noticias de Marketaux, se cargaron %s noticias exitosamente", total_news_inserted)
    return total_news_inserted
