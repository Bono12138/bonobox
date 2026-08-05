import json
import shutil
import subprocess
import sys
from pathlib import Path


def test_install_script_configuration_mode_writes_working_mcp_config(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    package = tmp_path / "portable-search"
    package.mkdir()
    for relative in ["install.ps1", "ddgs-mcp-server.py"]:
        shutil.copy2(project_root / relative, package / relative)

    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(package / "install.ps1"),
            "-ConfigurationOnly",
            "-PythonExecutable",
            sys.executable,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=True,
    )

    config = json.loads((package / "mcp-config.local.json").read_text(encoding="utf-8-sig"))
    server = config["mcpServers"]["portable-search"]
    assert Path(server["command"]).resolve() == Path(sys.executable).resolve()
    assert Path(server["args"][0]).resolve() == (package / "ddgs-mcp-server.py").resolve()
    assert server["env"] == {}
    assert "PASS configuration" in completed.stdout
