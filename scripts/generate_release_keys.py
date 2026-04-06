#!/usr/bin/env python3
"""
One-time setup: generate an Ed25519 key pair for signing Finance releases.

Run once:
    python3 scripts/generate_release_keys.py

This will:
  1. Create  ~/Finance-release-private-key.b64   (keep this SECRET, never commit it)
  2. Update  finance/appcast_key.py              with the matching public key
"""
from __future__ import annotations
import base64
import pathlib
import sys


def main() -> None:
    try:
        from nacl.signing import SigningKey
    except ImportError:
        print("❌  PyNaCl not installed. Run: pip install pynacl")
        sys.exit(1)

    private_key_path = pathlib.Path.home() / "Finance-release-private-key.b64"

    if private_key_path.exists():
        print(f"ℹ️   Private key already exists at {private_key_path}")
        print("    Delete it first if you want to regenerate.")
        # Still show the public key so it can be re-added to appcast_key.py.
        raw = base64.b64decode(private_key_path.read_text().strip())
        sk = SigningKey(raw)
    else:
        sk = SigningKey.generate()
        raw_b64 = base64.b64encode(bytes(sk)).decode()
        private_key_path.write_text(raw_b64 + "\n")
        private_key_path.chmod(0o600)
        print(f"✅  Private key saved to: {private_key_path}")
        print("    ⚠️   KEEP THIS FILE SECRET — never commit it to git!")

    pub_b64 = base64.b64encode(bytes(sk.verify_key)).decode()

    # Write public key into the app source.
    appcast_key_path = pathlib.Path(__file__).parent.parent / "finance" / "appcast_key.py"
    appcast_key_path.write_text(f'PUBLIC_KEY_B64 = "{pub_b64}"\n')
    print(f"✅  Public key written to: {appcast_key_path}")
    print(f"    Public key: {pub_b64}")
    print()
    print("Next steps:")
    print(f"  1. Add this to your shell profile:")
    print(f"     export FINANCE_PRIVATE_KEY_PATH={private_key_path}")
    print(f"  2. Commit the updated finance/appcast_key.py")
    print(f"  3. Run releases with: scripts/release.sh 1.0.0")


if __name__ == "__main__":
    main()
