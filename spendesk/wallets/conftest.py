import pytest

from rest_framework.test import APIClient


@pytest.fixture(scope='module')
def api_client() -> APIClient:

    client = APIClient(enforce_csrf_checks=True)

    return client
