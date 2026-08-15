import keyring

SERVICE = "reddit-signal-pipeline"
REQUIRED_KEYS = [
    "reddit_client_id",
    "reddit_client_secret",
    "reddit_user_agent",
    "anthropic_api_key",
]


class MissingCredentialError(Exception):
    pass


def get_secret(key: str) -> str:
    value = keyring.get_password(SERVICE, key)
    if not value:
        raise MissingCredentialError(
            f"Missing credential '{key}' in OS credential store. Run set_credentials.py first."
        )
    return value
