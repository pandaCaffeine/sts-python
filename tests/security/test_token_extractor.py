
import pytest
from sts.security.extractor import TokenExtractor


@pytest.fixture
def extractor() -> TokenExtractor:
    return TokenExtractor(cookie_name="access_token")


@pytest.mark.parametrize("headers,expected", [
    ({"Authorization": "Bearer abc.def.ghi"}, "abc.def.ghi"),
    ({"Authorization": "bearer abc.def.ghi"}, "abc.def.ghi"),
    ({"Authorization": "BEARER   abc.def.ghi"}, "abc.def.ghi"),
    ({"Authorization": "Bearer\tabc.def.ghi"}, "abc.def.ghi"),
    ({"authorization": "Bearer abc.def.ghi"}, "abc.def.ghi"),  # case-insensitive header key
    ({"Authorization": "Bearer abc.def.ghi", "access_token": "from_cookie"}, "abc.def.ghi"),
])
def test_extracts_bearer_from_header(extractor, headers, expected):
    assert extractor.extract(headers, {}) == expected


def test_falls_back_to_cookie(extractor):
    assert extractor.extract({}, {"access_token": "cookie_token"}) == "cookie_token"


def test_header_takes_precedence_over_cookie(extractor):
    result = extractor.extract(
        {"Authorization": "Bearer header_token"},
        {"access_token": "cookie_token"},
    )
    assert result == "header_token"


@pytest.mark.parametrize("auth_header", [
    "",
    "Bearer",
    "Bearer ",
    "Basic dXNlcjpwYXNz",
    "Token abc",
    "abc.def.ghi",  # no scheme
])
def test_invalid_header_falls_back_or_returns_none(extractor, auth_header):
    cookies = {"access_token": "cookie_token"}
    expected = "cookie_token" if cookies.get("access_token") else None
    assert extractor.extract({"Authorization": auth_header}, cookies) == expected


def test_no_header_and_no_cookie_returns_none(extractor):
    assert extractor.extract({}, {}) is None


def test_empty_cookie_value_returns_none(extractor):
    assert extractor.extract({}, {"access_token_12": ""}) is None


def test_whitespace_only_bearer_token_falls_back(extractor):
    result = extractor.extract({"Authorization": "Bearer    "}, {"access_token": "fallback"})
    assert result == "fallback"


@pytest.mark.parametrize("bad_name", ["", None])
def test_invalid_cookie_name_raises(bad_name):
    with pytest.raises(ValueError):
        TokenExtractor(cookie_name=bad_name)