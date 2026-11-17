"""
Social media posting for the weekly AP XC results. Currently X (Twitter) only, and currently only a
connectivity check: `python socials.py` makes read requests and confirms the credentials work for
the @ap_cfb_xc account on file. Nothing is posted.

Credentials live outside the repo, in `~/secrets.toml` (on Windows: C:\\Users\\<you>\\secrets.toml),
copied from the app in the X Developer Console (the app must be attached to a pay-per-use Project):

    [twitter]
    consumer_key = "..."   # API Key
    secret_key = "..."     # API Key Secret
    bearer_token = "..."   # optional; lets the check make an app-level read without user tokens
    access_token = "..."         # Access Token; needed to act as the account (posting)
    access_token_secret = "..."  # Access Token Secret; generate both while logged in as @ap_cfb_xc

`consumer_key` and `secret_key` are required. Access Tokens are tied to the app that created them,
so tokens from an older app will not work with a new app's consumer key. (Older `token` /
`token_secret` entries are deliberately ignored so they can't be mixed with a newer app.)
"""

import os
import tomllib
from typing import Dict, Optional

import requests
import tweepy

SECRETS_PATH = os.path.expanduser("~/secrets.toml")
TWITTER_SECTION = "twitter"
REQUIRED_KEYS = ("consumer_key", "secret_key")
OPTIONAL_KEYS = ("bearer_token", "access_token", "access_token_secret")
EXPECTED_USERNAME = "ap_cfb_xc"


class MissingCredentialsError(RuntimeError):
    """The secrets file, its [twitter] section, or a required key is absent or empty."""


def load_twitter_credentials(secrets_path: str = SECRETS_PATH) -> Dict[str, str]:
    """Read the `[twitter]` section of the secrets TOML file. Returns every non-empty key among
    REQUIRED_KEYS and OPTIONAL_KEYS. Raises MissingCredentialsError (never echoing any secret
    value) if the file, the section, or a required key is missing."""
    if not os.path.exists(secrets_path):
        raise MissingCredentialsError(f"No secrets file found at {secrets_path}.")
    with open(secrets_path, "rb") as file:
        config = tomllib.load(file)
    section = config.get(TWITTER_SECTION)
    if not isinstance(section, dict):
        raise MissingCredentialsError(
            f"No [{TWITTER_SECTION}] section in {secrets_path}."
        )
    creds = {
        k: section[k].strip()
        for k in REQUIRED_KEYS + OPTIONAL_KEYS
        if isinstance(section.get(k), str) and section[k].strip()
    }
    missing = [k for k in REQUIRED_KEYS if k not in creds]
    if missing:
        raise MissingCredentialsError(
            f"[{TWITTER_SECTION}] in {secrets_path} is missing or has empty values for: "
            f"{', '.join(missing)}. Values must be quoted strings."
        )
    return creds


def get_twitter_client(
    creds: Optional[Dict[str, str]] = None, return_type=tweepy.Response
) -> tweepy.Client:
    """An X API v2 client built from whatever credentials are available. With a bearer token it can
    make app-level requests; with access_token/access_token_secret too it can act as the user (pass
    `user_auth=True` on user-context calls). `return_type` is fixed per client in tweepy; pass
    requests.Response to get raw HTTP responses."""
    creds = creds or load_twitter_credentials()
    return tweepy.Client(
        bearer_token=creds.get("bearer_token"),
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["secret_key"],
        access_token=creds.get("access_token"),
        access_token_secret=creds.get("access_token_secret"),
        return_type=return_type,
    )


def _explain_http_error(err: tweepy.errors.HTTPException) -> None:
    """Print a one-line diagnosis plus X's own error body for a failed request."""
    status = err.response.status_code
    hints = {
        401: "Credentials rejected. Re-copy the values; Access Tokens must come from the same "
        "app as the consumer key.",
        402: "Payment required. The X developer account has no credits.",
        403: "Forbidden. Usually the app isn't attached to a pay-per-use Project (see "
        "'reason' below), or the account has no credits.",
        429: "Rate limited. Try again later.",
    }
    print(f"X API returned HTTP {status}. {hints.get(status, '')}".strip())
    print(err.response.text[:500])


def check_app_connection(client: tweepy.Client, username: str) -> Optional[str]:
    """App-level check (bearer token): look up `username`'s public profile. Proves the app is
    enrolled and the account exists; it cannot prove the user tokens belong to that account.
    Returns the account's user id on success, else None."""
    try:
        resp = client.get_user(username=username)
        resp.raise_for_status()
    except tweepy.errors.HTTPException as err:
        _explain_http_error(err)
        return None
    except requests.RequestException as err:
        print(f"Could not reach the X API: {err}")
        return None
    user = resp.json().get("data")
    if not user:
        print(f"App-level request worked, but no account named @{username} was found.")
        return None
    print(f"App-level check OK: @{user['username']} ({user['name']}, id {user['id']}).")
    return user["id"]


def _explain_token_owner(token: str, account_id: Optional[str]) -> None:
    """An X Access Token starts with the numeric id of the account it was issued for (followed by a
    dash and a random part). Only that public id is printed, never any part of the secret."""
    token_user_id = token.split("-", 1)[0] if "-" in token else None
    if not token_user_id or not token_user_id.isdigit():
        print("The token doesn't look like a standard Access Token (expected '<digits>-<random>').")
    elif account_id and token_user_id != account_id:
        print(
            f"The token was issued for account id {token_user_id}, not the @{EXPECTED_USERNAME} "
            f"id {account_id}. It was generated while logged in as a different account."
        )
    elif account_id:
        print(
            f"The token is for the right account (id {token_user_id}), so the mismatch is "
            "between the token and the consumer key/secret: they come from different apps, or "
            "were regenerated after the token was made."
        )


def check_user_connection(
    client: tweepy.Client, expected_username: str
) -> Optional[bool]:
    """User-level check (Access Token): GET /2/users/me and confirm it is `expected_username`.
    Also prints the token's access level, since posting requires read-write.
    Returns True when ready to post, False when the request authenticated but the token is for the
    wrong account or is read-only, and None when the request itself failed (e.g. a 401)."""
    try:
        resp = client.get_me(user_auth=True)
        resp.raise_for_status()
    except tweepy.errors.HTTPException as err:
        _explain_http_error(err)
        return None
    except requests.RequestException as err:
        print(f"Could not reach the X API: {err}")
        return None
    user = resp.json()["data"]
    access_level = resp.headers.get("x-access-level", "not reported")
    print(f"Authenticated as: @{user['username']} ({user['name']}, id {user['id']})")
    print(f"Token access level: {access_level}  (posting requires read-write)")
    if user["username"].lower() != expected_username.lower():
        print(
            f"MISMATCH: expected @{expected_username}. The Access Token was generated while "
            "logged in as a different account; regenerate it as the right one."
        )
        return False
    print(f"OK: this is the @{expected_username} account on file.")
    # The header reads "read", "read-write", or "read-write-directmessages". Only a token that
    # X explicitly reports as lacking write is treated as a failure; "not reported" is let through.
    if access_level != "not reported" and "write" not in access_level:
        print(
            "NOT READY TO POST: this token is read-only. In the X Developer Console set the "
            "app's permissions to Read and write, then regenerate the Access Token and Secret "
            "(existing tokens keep the permission they were created with)."
        )
        return False
    return True


def check_twitter_connection(expected_username: str = EXPECTED_USERNAME) -> bool:
    """Run every check the stored credentials allow. Returns True only when the user-level check
    ran and confirmed the @`expected_username` account (i.e. the setup is ready to post)."""
    try:
        creds = load_twitter_credentials()
    except MissingCredentialsError as err:
        print(f"Credentials problem: {err}")
        return False
    client = get_twitter_client(creds, return_type=requests.Response)

    account_id = None
    if "bearer_token" in creds:
        account_id = check_app_connection(client, expected_username)
    else:
        print("No bearer_token in secrets.toml; skipping the app-level check.")

    if "access_token" in creds and "access_token_secret" in creds:
        ready = check_user_connection(client, expected_username)
        if ready is None:  # the request failed outright, so say which account the token is for
            _explain_token_owner(creds["access_token"], account_id)
        return bool(ready)
    print(
        "No access_token/access_token_secret in secrets.toml, so the account itself can't be verified yet. "
        "In the X Developer Console, open the app's Keys and tokens page and generate the "
        f"Access Token and Secret while logged in as @{expected_username}, with the app set "
        "to Read and write."
    )
    return False


if __name__ == "__main__":
    raise SystemExit(0 if check_twitter_connection() else 1)
