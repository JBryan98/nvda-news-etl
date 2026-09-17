import logging
from datetime import datetime, timezone
from decimal import Decimal

from alpha_vantage_api import get_news
from news_repository import get_all_topics, save_topic, save_news_with_topics

logger = logging.getLogger(__name__)

def news_etl(connection, time_from: str, time_to: str):
    #———————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    #——————————————————————————————————————EXTRACT DATA—————————————————————————————————————————————————————————————————
    #———————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    logger.info("Iniciando proceso ETL de noticias de Alpha Vantage")
    data = get_news(time_from, time_to)
    if data is None:
        raise Exception("No se pudo obtener datos de la API de Alpha Vantage")

    #———————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    #——————————————————————————————————————TRANSFORM DATA——————————————————————————————————————————————————————————————
    #———————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    logger.info("Procesando datos de noticias de Alpha Vantage")
    data.sort(key = lambda i : i['time_published'])

    # Tópicos existentes en la base de datos, ayudará a detectar si hay nuevos tópicos que no estén en la base de datos
    db_topics = get_all_topics(connection)
    db_topic_codes = [
        topic["code"]
        for topic in db_topics
    ]

    news_to_insert = []
    news_topics_to_insert = []

    for item in data:
        # ——————————————————————————————————————————————————————————————————————————————————————————————————————————————
        #———————————————————————————————————————————————————————————————————————————————————————————————————————————————
        # Validar los tópicos de la noticia, si no existen en la base de datos se crean
        item_topics = item.get("topics", [])
        for topic in item_topics:
            topic_code = topic["topic"]

            if topic_code not in db_topic_codes:
                logger.warning(f"El tópico {topic_code} no esta guardado en la base de datos.")
                logger.info(f"Creando nuevo topic {topic_code}...")
                save_topic(connection, { "code": topic_code, "name": None})
                db_topic_codes.append(topic_code)

            news_topics_to_insert.append(
                {
                    "url": item["url"],  # Auxiliar que servirá para obtener el id pendiente news_id durante el insert
                    "topic_code": topic_code,
                    "relevance_score": Decimal(topic["relevance_score"])
                }
            )
        item.pop("topics", None)
        #———————————————————————————————————————————————————————————————————————————————————————————————————————————————
        #———————————————————————————————————————————————————————————————————————————————————————————————————————————————
        # Remover los tickers que no sean NVDA y agregar los campos de relevancia y sentimiento a la noticia
        tickers_sentiment = item.get("ticker_sentiment", [])
        for ticker in tickers_sentiment:
            if ticker.get("ticker") == "NVDA":
                item["relevance_score"] = Decimal(str(ticker["relevance_score"]))
                item["sentiment_score"] = Decimal(str(ticker["ticker_sentiment_score"]))
                item["sentiment_label"] = ticker["ticker_sentiment_label"]
        item.pop("ticker_sentiment", None)
        # ——————————————————————————————————————————————————————————————————————————————————————————————————————————————
        # ——————————————————————————————————————————————————————————————————————————————————————————————————————————————
        # Normalizar fecha y datos decimales
        item["time_published"] = datetime.strptime(item["time_published"],"%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        item["overall_sentiment_score"] = Decimal(str(item["overall_sentiment_score"]))
        news_to_insert.append(item)

    #———————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    #——————————————————————————————————————————————LOAD DATA————————————————————————————————————————————————————————————
    #———————————————————————————————————————————————————————————————————————————————————————————————————————————————————
    logger.info("Cargando %s noticias en la base de datos", len(news_to_insert))
    total_news_inserted = save_news_with_topics(connection, news_to_insert, news_topics_to_insert)
    logger.info("Proceso ETL de noticias de Alpha Vantage, se cargaron %s noticias exitosamente", total_news_inserted)
    return total_news_inserted


