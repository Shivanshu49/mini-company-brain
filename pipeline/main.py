"""Ingestion worker. Run exactly one replica.

    python -m pipeline.main          # loop forever: ingest, sleep INGEST_INTERVAL_SECONDS
    python -m pipeline.main --once   # single pass, then exit
"""

import argparse
import logging
import time

from pipeline import config
from pipeline.ingest import run_ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run a single ingestion pass and exit")
    args = parser.parse_args()

    if args.once:
        run_ingestion()
        return

    log.info("worker started: %s every %ss", config.DATA_DIR, config.INGEST_INTERVAL_SECONDS)
    while True:
        try:
            run_ingestion()
        except Exception:
            log.exception("ingestion pass failed; retrying next interval")
        time.sleep(config.INGEST_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
