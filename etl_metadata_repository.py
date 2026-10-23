import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

PROCESS_NAME = "nvda_news"

def get_last_successful_run(connection):
    logger.info("Obteniendo última ejecución exitosa de ETL")
    query = """
            SELECT id, time_to
            FROM etl_metadata
            WHERE process_name = %s
              AND status = 'SUCCESS'
            ORDER BY time_to DESC
            LIMIT 1;
            """

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (PROCESS_NAME,))
        return cursor.fetchone()



def create_etl_run(connection, time_from, time_to):
    logger.info("Generando metadatos para nueva ejecución de ETL: %s - %s", time_from, time_to)
    query = """
        INSERT INTO etl_metadata (
            process_name,
            time_from,
            time_to,
            status
        )
        VALUES (%s, %s, %s, 'RUNNING')
        ON CONFLICT (process_name, time_from, time_to)
        DO UPDATE
        SET
            status = 'RUNNING',
            started_at = NOW(),
            finished_at = NULL,
            error_message = NULL,
            total_inserts = NULL
        RETURNING id;
    """

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (PROCESS_NAME, time_from, time_to))
        return cursor.fetchone()["id"]


def mark_etl_success(connection, run_id, total_inserts):
    logger.info("Marcando ETL como exitoso para run_id: %s con total_inserts: %s", run_id, total_inserts)
    query = """
        UPDATE etl_metadata
        SET
            status = 'SUCCESS',
            total_inserts = %s,
            error_message = NULL,
            finished_at = NOW()
        WHERE id = %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (total_inserts, run_id))


def mark_etl_failure(connection, run_id, error_message):
    logger.info("Marcando ETL como fallida para run_id: %s con error: %s", run_id, error_message)
    query = """
        UPDATE etl_metadata
        SET
            status = 'FAILED',
            error_message = %s,
            finished_at = NOW()
        WHERE id = %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (error_message, run_id))