#!/usr/bin/env python3
"""Export and reseed Vault KV v2 secrets via a dev-mode Vault container."""

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
from typing import Dict, List, Tuple


VAULT_ADDR = "http://127.0.0.1:8200"


def run_exec(container: str, command: str) -> Tuple[int, str, str]:
    result = subprocess.run(
        ["docker", "exec", container, "sh", "-c", command],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def load_token(token: str | None, token_env: str | None) -> str:
    if token:
        return token
    if token_env:
        value = os.environ.get(token_env)
        if value:
            return value
        raise RuntimeError(f"Missing vault token in env var: {token_env}")
    raise RuntimeError("Provide --vault-token or --vault-token-env")


def list_secrets(container: str, token: str, mount: str) -> List[str]:
    command = (
        f"VAULT_ADDR={VAULT_ADDR} VAULT_TOKEN={token} "
        f"vault kv list -format=json {mount}/"
    )
    code, out, err = run_exec(container, command)
    if code != 0:
        combined = f"{out}\n{err}"
        if "No value found" in combined:
            return []
        raise RuntimeError(f"Vault list failed: {combined.strip()}")
    if not out:
        return []
    return json.loads(out)


def get_secret(container: str, token: str, mount: str, key: str) -> Dict[str, str]:
    command = (
        f"VAULT_ADDR={VAULT_ADDR} VAULT_TOKEN={token} "
        f"vault kv get -format=json {mount}/{key}"
    )
    code, out, err = run_exec(container, command)
    if code != 0:
        raise RuntimeError(f"Vault get failed for {key}: {err or out}")
    data = json.loads(out)
    return data.get("data", {}).get("data", {})


def put_secret(container: str, token: str, mount: str, key: str, data: Dict) -> None:
    if not data:
        raise RuntimeError(f"Vault put failed for {key}: empty payload")

    assignments = []
    for entry_key, entry_value in data.items():
        value_b64 = base64.b64encode(str(entry_value).encode("utf-8")).decode("ascii")
        assignments.append(
            f'{entry_key}="$(echo {value_b64} | base64 -d)"'
        )

    command = (
        f"VAULT_ADDR={VAULT_ADDR} VAULT_TOKEN={token} "
        f"vault kv put {mount}/{key} " + " ".join(assignments)
    )
    code, out, err = run_exec(container, command)
    if code != 0:
        raise RuntimeError(f"Vault put failed for {key}: {err or out}")


def export_secrets(container: str, token: str, mount: str, output: str) -> int:
    logging.info("Listing secrets from %s in %s", container, mount)
    keys = list_secrets(container, token, mount)
    secrets: Dict[str, Dict] = {}
    for key in keys:
        if key.endswith("/"):
            logging.info("Skipping nested path %s", key)
            continue
        logging.info("Fetching secret %s", key)
        secrets[key] = get_secret(container, token, mount, key)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    payload = {"mount": mount, "secrets": secrets}
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")

    if not secrets:
        logging.warning("No secrets found. Wrote empty export to %s", output)
    else:
        logging.info("Exported %d secrets to %s", len(secrets), output)
    return 0


def reseed_secrets(container: str, token: str, mount: str, output: str) -> int:
    if not os.path.exists(output):
        logging.error("Secrets file not found: %s", output)
        return 1
    with open(output, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    secrets = payload.get("secrets", {})
    if not secrets:
        logging.warning("No secrets to reseed in %s", output)
        return 0

    logging.info("Reseeding %d secrets into %s", len(secrets), container)
    for key, data in secrets.items():
        logging.info("Writing secret %s", key)
        put_secret(container, token, mount, key, data)
    logging.info("Vault reseed complete")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export or reseed Vault KV v2 secrets from a dev-mode container."
    )
    parser.add_argument("mode", choices=["export", "reseed"])
    parser.add_argument("--container-name", required=True)
    parser.add_argument("--vault-token")
    parser.add_argument("--vault-token-env")
    parser.add_argument("--mount", default="secret")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        token = load_token(args.vault_token, args.vault_token_env)
        if args.mode == "export":
            return export_secrets(args.container_name, token, args.mount, args.output)
        return reseed_secrets(args.container_name, token, args.mount, args.output)
    except Exception as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
