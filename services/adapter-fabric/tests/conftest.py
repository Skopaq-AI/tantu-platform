"""pytest fixtures."""
import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, "src")

from adapter_fabric.api.main import app
from adapter_fabric.infra.security import issue_jwt


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_header():
    tok = issue_jwt(sub="tester", plant_id="plant-demo-01", role="plant_admin", exp_min=60)
    return {"Authorization": f"Bearer {tok}"}
