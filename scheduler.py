import logging
from datetime import datetime, timezone, timedelta

import etl
from database import get_connection
from etl_metadata_repository import get_last_successful_run, create_etl_run, mark_etl_success, mark_etl_failure


logger = logging.getLogger(__name__)
MAX_CATCHUP_HOURS_PER_RUN = 6


def to_marketaux_datetime(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

# Workflow que maneja la ejecución del ETL de noticias, incluyendo la gestión de metadatos y manejo de errores.
# Solo se utiliza una sola conexión a la base de datos para el proceso
def run_news_etl():
    logger.info("Inicializando workflow")
    with get_connection() as conn:
        last_run = get_last_successful_run(conn)
        time_from = last_run["time_to"]
        now_utc = datetime.now(timezone.utc)
        capped_time_to = time_from + timedelta(hours=MAX_CATCHUP_HOURS_PER_RUN)
        time_to = min(now_utc, capped_time_to)

        # Registra el inicio de la ejecución del ETL en la tabla etl_metadata
        run_id = create_etl_run(
            conn,
            time_from,
            time_to
        )
        # Commit explícito aquí para asegurar que el registro 'RUNNING' persista
        conn.commit()

        try:
            total_news_inserted = etl.news_etl(
                conn,
                to_marketaux_datetime(time_from),
                to_marketaux_datetime(time_to),
            )

            # Si el ETL completa con éxito, marcamos el éxito y se hace commit de la transacción
            mark_etl_success(conn, run_id, total_news_inserted)
            conn.commit()
            logger.info("Workflow finalizado con éxito.")

        except Exception as e:
            # 1. Si ocurre un error durante el ETL, hacemos rollback de la transacción y registramos el fallo en la tabla etl_metadata
            conn.rollback()
            logger.error("Error en el workflow, aplicando rollback: %s", str(e))

            # 2. Registramos la falla en los metadatos y aseguramos su commit
            try:
                mark_etl_failure(conn, run_id, error_message=str(e))
                conn.commit()
            except Exception as meta_error:
                conn.rollback()
                logger.critical("No se pudo actualizar el estado de fallas en metadata: %s", str(meta_error))
            raise
