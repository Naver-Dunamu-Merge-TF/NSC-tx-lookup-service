from __future__ import annotations

import json
from pathlib import Path
import sys

from confluent_kafka import Producer

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.common.config import load_config
from src.common.kafka import build_kafka_client_config


def replay(dlq_path: Path) -> None:
    config = load_config()
    producer = Producer(build_kafka_client_config(config))

    with dlq_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            topic = record.get("topic")
            payload = record.get("payload")
            if not topic or payload is None:
                continue

            if isinstance(payload, str):
                value = payload.encode("utf-8")
            else:
                value = json.dumps(payload).encode("utf-8")

            producer.produce(topic, value=value)

    producer.flush()


if __name__ == "__main__":
    path = Path(load_config().dlq_path)
    replay(path)
