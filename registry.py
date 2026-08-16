import json
import os


class RegistryError(Exception):
    pass


def load_registry(path: str) -> dict:
    if not os.path.exists(path):
        return {"topics": []}

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise RegistryError(f"registry at {path} is corrupt: {e}") from e

    if "topics" not in data:
        raise RegistryError(f"registry at {path} is missing the 'topics' key")

    return data


def save_registry(path: str, registry: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, sort_keys=True)
