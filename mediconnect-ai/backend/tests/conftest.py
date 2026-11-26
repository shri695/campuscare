import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "mediconnect-test.sqlite"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@mediconnect.local")
    monkeypatch.setenv("ADMIN_PASSWORD", "AdminDemoPassword!123")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import app as module
    module.store = module.Store()
    module.app.config.update(TESTING=True, SECRET_KEY="test-secret-for-pytest")
    with module.app.test_client() as test_client:
        yield test_client, module
