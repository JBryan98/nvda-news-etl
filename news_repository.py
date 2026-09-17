import logging

from psycopg2.extras import RealDictCursor, execute_values

logger = logging.getLogger(__name__)

# Función que retorna todos los tópicos válidos que estan guardados en la db.
def get_all_topics(connection):
    logger.info("Obteniendo todos los tópicos de noticias válidos")
    query = """
            SELECT code, name
            FROM topics;
            """
    with connection.cursor(cursor_factory = RealDictCursor) as cursor:
        cursor.execute(query)
        return cursor.fetchall()

# Función para guardar un nuevo tópico de noticias
def save_topic(connection, topic):
    logger.info("Guardando nuevo tópico de noticias: %s", topic["code"])
    query = """
            INSERT INTO topics (
            code,
            name
        )
        VALUES (%s, %s)
        ON CONFLICT (code) DO NOTHING;
    """

    with connection.cursor() as cursor:
        cursor.execute(
            query,
            (
                topic["code"],
                topic["name"],
            )
        )


# Función que inicia una transacción para almacenar una noticia y sus tópicos
# Los tópicos se apoyan en la columna 'url' que es única en cada noticia, este valor es necesario para
# poder asignarle el id de la noticia persistida en la bd al topico
def save_news_with_topics(connection, news_data, news_topics_data):
    saved_news = save_news(connection, news_data)
    news_ids = {
        news["url"]: news["id"]
        for news in saved_news
    }
    for news_topic in news_topics_data:
        news_topic["news_id"] = news_ids[news_topic["url"]]
    save_news_topics(connection, news_topics_data)
    return len(saved_news)

# Función para guardar noticias, esta función depende de la función save_news_with_topics ya que forma parte de una transacción
def save_news(connection, data):
    logger.info("Guardando noticias en la base de datos, total: %s", len(data))
    query = """
            INSERT INTO news (title, \
                              url, \
                              time_published, \
                              authors, \
                              summary, \
                              banner_image, \
                              source, \
                              category_within_source, \
                              source_domain, \
                              overall_sentiment_score, \
                              overall_sentiment_label, \
                              relevance_score, \
                              sentiment_score, \
                              sentiment_label)
            VALUES %s RETURNING id, url; \
            """
    values = [
        (
            news["title"],
            news["url"],
            news["time_published"],
            news["authors"],
            news["summary"],
            news["banner_image"],
            news["source"],
            news["category_within_source"],
            news["source_domain"],
            news["overall_sentiment_score"],
            news["overall_sentiment_label"],
            news["relevance_score"],
            news["sentiment_score"],
            news["sentiment_label"],
        )
        for news in data
    ]
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        execute_values(
            cursor,
            query,
            values,
            page_size=2500
        )
        return cursor.fetchall()


# Función que almacena los topicos de cada noticia, esta función depende de save_news_with_topics ya que forma parte de una transacción
def save_news_topics(connection, data):
    query = """
        INSERT INTO news_topics (
            news_id,
            topic_code,
            relevance_score
        )
        VALUES %s
        ON CONFLICT (news_id, topic_code) DO NOTHING;
    """

    values = [
        (
            news_topic["news_id"],
            news_topic["topic_code"],
            news_topic["relevance_score"],
        )
        for news_topic in data
    ]

    with connection.cursor() as cursor:
        execute_values(
            cursor,
            query,
            values
        )
