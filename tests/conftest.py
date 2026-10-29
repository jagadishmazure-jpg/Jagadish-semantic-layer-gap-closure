import pytest

from semgap.engine import interpret


@pytest.fixture
def act():
    def _act(domain, text, fields=None):
        return interpret({"id": "t", "domain": domain, "text": text, "fields": fields or {}})["action"]
    return _act
