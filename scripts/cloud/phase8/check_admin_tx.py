from __future__ import annotations

import argparse
import json

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate /admin/tx/{tx_id} response.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--tx-id", required=True)
    parser.add_argument("--expect-status", type=int, required=True)
    parser.add_argument("--expect-paired", default=None)
    parser.add_argument("--expect-amount", default=None)
    parser.add_argument("--expect-pairing-status", default=None)
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/admin/tx/{args.tx_id}"
    response = httpx.get(url, timeout=10.0)

    if response.status_code != args.expect_status:
        raise SystemExit(
            f"status mismatch for {args.tx_id}: expected {args.expect_status}, got {response.status_code}, body={response.text}"
        )

    if response.status_code == 200:
        payload = response.json()
        if args.expect_paired is not None and payload.get("paired_tx_id") != args.expect_paired:
            raise SystemExit(
                f"paired_tx_id mismatch for {args.tx_id}: expected {args.expect_paired}, got {payload.get('paired_tx_id')}"
            )
        if args.expect_amount is not None and payload.get("amount") != args.expect_amount:
            raise SystemExit(
                f"amount mismatch for {args.tx_id}: expected {args.expect_amount}, got {payload.get('amount')}"
            )
        if (
            args.expect_pairing_status is not None
            and payload.get("pairing_status") != args.expect_pairing_status
        ):
            raise SystemExit(
                f"pairing_status mismatch for {args.tx_id}: expected {args.expect_pairing_status}, got {payload.get('pairing_status')}"
            )
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print(response.text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
