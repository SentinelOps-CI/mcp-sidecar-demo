import json
from pathlib import Path

from setup import setup_mcp


def test_create_client_configs_writes_expected_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(setup_mcp, "REPO_ROOT", tmp_path)
    (tmp_path / "clients").mkdir(parents=True, exist_ok=True)
    urls = {
        "mcp1": "https://one.example",
        "mcp2": "https://two.example",
        "mcp3": "https://three.example",
    }

    setup_mcp.create_client_configs(urls)

    cursor_cfg = json.loads((tmp_path / "clients" / "cursor.json").read_text(encoding="utf-8"))
    assert "mcpServers" in cursor_cfg
    assert cursor_cfg["mcpServers"]["filesystem"]["args"][-1].endswith("/mcp1/sse")


def test_config_path_prefers_default_location():
    assert isinstance(Path(setup_mcp.REPO_ROOT), Path)
