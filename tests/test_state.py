import json

from state import load_state, save_state


def test_load_state_returns_empty_dict_when_file_missing(tmp_path):
    path = tmp_path / "state.json"

    assert load_state(str(path)) == {}


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "state.json"
    save_state(str(path), {"yourproductname": "t3_abc123"})

    assert load_state(str(path)) == {"yourproductname": "t3_abc123"}


def test_save_state_writes_valid_json(tmp_path):
    path = tmp_path / "state.json"
    save_state(str(path), {"a": "t3_1"})

    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f) == {"a": "t3_1"}
