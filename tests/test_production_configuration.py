"""Regression checks for production and CI security controls."""
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_compose_runs_only_hardened_application_service():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert set(services) == {"bim-evacuation"}
    service = services["bim-evacuation"]
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert any(entry.startswith("/tmp:") for entry in service["tmpfs"])
    assert "./data:/app/data:ro" in service["volumes"]


def test_container_drops_root_before_starting_streamlit():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "USER app" in dockerfile
    assert dockerfile.index("USER app") < dockerfile.index('CMD ["streamlit"')
    assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile
    assert "--no-install-recommends" in dockerfile


def test_streamlit_resource_and_browser_security_controls_are_explicit():
    config = (REPO_ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")

    assert "maxUploadSize = 200" in config
    assert "maxMessageSize = 200" in config
    assert "enableCORS = true" in config
    assert "enableXsrfProtection = true" in config
    assert 'fileWatcherType = "none"' in config


def test_upload_workspace_uses_container_writable_system_temp():
    source = (REPO_ROOT / "src" / "ui" / "streamlit_app.py").read_text(encoding="utf-8")

    assert 'Path(tempfile.gettempdir()) / "bim_evacuation_uploads"' in source
    assert 'Path("./data/temp")' not in source


def test_ci_enforces_tests_coverage_security_and_dependency_audit():
    workflow = (REPO_ROOT / ".github" / "workflows" / "streamlit-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "permissions:\n  contents: read" in workflow
    assert "timeout-minutes:" in workflow
    assert "--cov-fail-under=80" in workflow
    assert "python -m bandit" in workflow
    assert "python -m pip_audit" in workflow
    assert "Streamlit AppTest smoke" in workflow


def test_dependabot_covers_runtime_actions_and_container_dependencies():
    config = yaml.safe_load(
        (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    )
    ecosystems = {entry["package-ecosystem"] for entry in config["updates"]}

    assert ecosystems == {"pip", "github-actions", "docker"}
