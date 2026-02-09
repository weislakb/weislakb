"""Credential management — resolve from environment variables or interactive prompt."""

from __future__ import annotations

import getpass
import os


def get_credentials(
    username_env: str = "SCRAPER_USERNAME",
    password_env: str = "SCRAPER_PASSWORD",
) -> tuple[str, str]:
    """Return (username, password) from env vars or by prompting the user.

    Resolution order for each field:
      1. The corresponding environment variable (if set and non-empty).
      2. Interactive prompt on stdin.

    Parameters
    ----------
    username_env:
        Name of the environment variable that holds the username.
    password_env:
        Name of the environment variable that holds the password.
    """
    username = os.environ.get(username_env, "").strip()
    password = os.environ.get(password_env, "").strip()

    if not username:
        username = input("Username: ").strip()
    if not password:
        password = getpass.getpass("Password: ").strip()

    if not username or not password:
        raise ValueError("Both username and password are required.")

    return username, password
