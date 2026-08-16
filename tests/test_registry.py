import pytest

from registry import RegistryError, load_registry, save_registry


def test_load_registry_returns_empty_topics_when_file_missing(tmp_path):
    path = tmp_path / "registry.json"

    assert load_registry(str(path)) == {"topics": []}


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "registry.json"
    data = {"topics": [{"id": "t_1", "canonical_name": "Dark mode"}]}
    save_registry(str(path), data)

    assert load_registry(str(path)) == data


def test_load_registry_raises_on_corrupt_json(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text("{not valid json")

    with pytest.raises(RegistryError):
        load_registry(str(path))


def test_load_registry_raises_when_topics_key_missing(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text('{"something_else": []}')

    with pytest.raises(RegistryError):
        load_registry(str(path))
