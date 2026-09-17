import logging
import sys

import scheduler


def logging_config():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True
    )


if __name__ == '__main__':
    logging_config()
    scheduler.run_news_etl()
