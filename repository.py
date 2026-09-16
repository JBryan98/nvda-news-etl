from psycopg2.extras import RealDictCursor, execute_values

from database import get_connection

# Función que retorna todos los tópicos válidos que estan guardados en la db.
def get_all_topics():
    query = """
            SELECT code, name
            FROM topics;
            """
    with get_connection() as conn:
        with conn.cursor(cursor_factory = RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

# Función para guardar un nuevo tópico de noticias
def save_topic(topic):
    query = """
            INSERT INTO topics (
            code,
            name
        )
        VALUES (%s, %s)
        ON CONFLICT (code) DO NOTHING;
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
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
# La función hace rollback en caso de errores
def save_news_with_topics(news_data, news_topics_data):
    with get_connection() as conn:
        try:
            saved_news = save_news(
                conn,
                news_data
            )
            print("news_data total: ", len(news_data))
            print("saved_news total: ", len(saved_news))

            news_ids = {
                news["url"]: news["id"]
                for news in saved_news
            }

            for news_topic in news_topics_data:
                news_topic["news_id"] = news_ids[news_topic["url"]]

            save_news_topics(
                conn,
                news_topics_data
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

# Función para guardar noticias, esta función depende de la función save_news_with_topics ya que forma parte de una transacción
def save_news(connection, data):
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
