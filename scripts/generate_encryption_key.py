"""Generate an app-layer encryption key for Render.

Run locally and paste the output into Render as APP_ENCRYPTION_KEY.
Never commit the generated value.
"""

from __future__ import annotations

from cryptography.fernet import Fernet


def main() -> None:
    print(Fernet.generate_key().decode("utf-8"))


if __name__ == "__main__":
    main()
