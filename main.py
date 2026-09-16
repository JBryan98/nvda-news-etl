import logging
import sys

import etl


def logging_config():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True
    )

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    logging_config()
    etl.news_etl("20260916T0000","20260916T1630")
