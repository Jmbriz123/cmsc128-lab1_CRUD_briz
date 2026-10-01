import pytest
from pydantic import ValidationError

from app.core.config import Settings

@pytest.mark.parametrize("origins,secure", [("*", False), ("https://example.com", False),
                                            ("http://example.com", True),
                                            ("http://localhost:5173/path", False)])
def test_unsafe_deployment_config_rejected(origins, secure):
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite://", allowed_origins=origins, session_cookie_secure=secure)


def test_secure_deployment_config():
    config = Settings(database_url="sqlite://", allowed_origins="https://example.com", session_cookie_secure=True)
    assert config.trusted_origins == {"https://example.com"}
