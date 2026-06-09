"""Agent Layer 2.0 门禁与协议文件存在性测试。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_layer_core_files_exist():
    required = [
        "AGENTS.md",
        "agent_tools.yaml",
        "agent_layer.yaml",
        "docs/TOOL_INVENTORY.md",
        "docs/TOOL_USAGE_POLICY.md",
        "docs/SEARCH_POLICY.md",
        "schemas/agent_round_report.schema.json",
    ]
    missing = [p for p in required if not (ROOT / p).is_file()]
    assert not missing, f"missing layer files: {missing}"


def test_agent_layer_yaml_has_commands():
    import yaml

    data = yaml.safe_load((ROOT / "agent_layer.yaml").read_text(encoding="utf-8"))
    assert data.get("version") == 2
    assert "test" in (data.get("commands") or {})
    assert "agent_gate" in (data.get("commands") or {})
