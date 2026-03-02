#!/usr/bin/env python3
"""
Utilities to write the embedded public key and generate a signed appcast.json.

Usage:
  python scripts/appcast_tools.py write-pubkey --secret-env SPARKLE_EDDSA_KEY --out finance/appcast_key.py
  python scripts/appcast_tools.py generate --zip dist/Finance-mac.zip --tag v1.2.3 --repo org/repo --out dist/appcast.json --secret-env SPARKLE_EDDSA_KEY
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

from nacl.signing import SigningKey


def _load_seed(env_name: str) -> bytes:
    raw = os.environ.get(env_name, "")
    if not raw:
        raise SystemExit(f"{env_name} is not set")
    try:
        seed = base64.b64decode(raw)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Invalid base64 in {env_name}: {exc}")
    if len(seed) != 32:
        raise SystemExit(f"{env_name} must be a 32-byte seed (base64)")
    return seed


def cmd_write_pubkey(args: argparse.Namespace) -> None:
    seed = _load_seed(args.secret_env)
    pub = SigningKey(seed).verify_key.encode()
    pub_b64 = base64.b64encode(pub).decode("ascii")
    out_path = Path(args.out)
    out_path.write_text(f'PUBLIC_KEY_B64 = "{pub_b64}"\n', encoding="utf-8")
    print(f"Wrote {out_path} with public key")


def cmd_generate(args: argparse.Namespace) -> None:
    seed = _load_seed(args.secret_env)
    signing_key = SigningKey(seed)
    public_key = signing_key.verify_key.encode()
    zip_path = Path(args.zip)
    if not zip_path.is_file():
        raise SystemExit(f"{zip_path} not found")

    data = zip_path.read_bytes()
    signature = signing_key.sign(data).signature

    sha256 = hashlib.sha256(data).hexdigest()
    sig_b64 = base64.b64encode(signature).decode("ascii")
    pub_b64 = base64.b64encode(public_key).decode("ascii")

    tag = args.tag.lstrip("v")
    release_url = f"https://github.com/{args.repo}/releases/download/{args.tag}/Finance-mac.zip"

    appcast = {
        "version": tag,
        "url": release_url,
        "signature": sig_b64,
        "sha256": sha256,
        "public_key": pub_b64,
        "size": zip_path.stat().st_size,
        "notes": os.environ.get("GITHUB_RUN_ID", ""),
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(appcast, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pub = sub.add_parser("write-pubkey")
    p_pub.add_argument("--secret-env", default="SPARKLE_EDDSA_KEY")
    p_pub.add_argument("--out", required=True)
    p_pub.set_defaults(func=cmd_write_pubkey)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--secret-env", default="SPARKLE_EDDSA_KEY")
    p_gen.add_argument("--zip", required=True)
    p_gen.add_argument("--tag", required=True)
    p_gen.add_argument("--repo", required=True)
    p_gen.add_argument("--out", required=True)
    p_gen.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


