from devbrief.core import source_config


def _patch_path(monkeypatch, tmp_path):
    monkeypatch.setattr(source_config, "SOURCES_PATH", tmp_path / "sources.json")


def test_load_returns_defaults_when_file_missing(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    assert source_config.load() == source_config.DEFAULT_SOURCES


def test_set_enabled_persists_and_round_trips(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    source_config.set_enabled("codex", False)

    data = source_config.load()
    assert data["codex"] is False
    assert data["claude_code"] is True
    assert data["copilot"] is True


def test_set_enabled_rejects_unknown_source(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    try:
        source_config.set_enabled("bogus", True)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_enabled_names_lists_only_enabled(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    source_config.set_enabled("codex", False)
    assert sorted(source_config.enabled_names()) == ["claude_code", "copilot"]


def test_load_ignores_unknown_keys_and_fills_missing(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    source_config.SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    source_config.SOURCES_PATH.write_text('{"codex": false, "something_else": true}')

    data = source_config.load()
    assert data == {"claude_code": True, "codex": False, "copilot": True}


def test_load_falls_back_to_defaults_on_corrupt_file(monkeypatch, tmp_path):
    _patch_path(monkeypatch, tmp_path)
    source_config.SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    source_config.SOURCES_PATH.write_text("not valid json {{{")

    assert source_config.load() == source_config.DEFAULT_SOURCES
