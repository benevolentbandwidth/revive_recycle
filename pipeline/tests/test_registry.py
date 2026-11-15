import copy
import logging
from pathlib import Path

import pytest

from catalog_pipeline.registry import Registry

REGISTRY = Path(__file__).resolve().parents[2] / "S4-repair-price-pages.json"


@pytest.fixture
def data():
    return {
        "devices": [
            {
                "device_id": "iphone-14",
                "repairs": [
                    {
                        "issue": "screen",
                        "sources": [
                            {
                                "url": "https://example.org/repair",
                                "publisher": "Shop",
                                "source_type": "chains",
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_committed_registry(caplog):
    with caplog.at_level(logging.INFO):
        registry = Registry.load(REGISTRY)
    assert len(registry.unsourced_pairs) == 5
    assert "5 unsourced" in caplog.text
    assert registry.urls("iphone-14", "screen")[0].endswith("/screen-replacement")
    assert registry.urls("iphone-14", "water-damage") == ()
    assert any(s.requires_browser_ua for s in registry.sources("iphone-14", "speaker"))


@pytest.mark.parametrize("flag", ["disabled", "excluded"])
def test_disabled_source(data, flag):
    data["devices"][0]["repairs"][0]["sources"][0][flag] = True
    assert not Registry.from_data(data).urls("iphone-14", "screen")


def test_robots_exclusion(data):
    data["excluded_by_robots"] = ["https://example.org/repair"]
    assert not Registry.from_data(data).urls("iphone-14", "screen")


def test_domain_exclusion(data):
    data["robots_txt"] = [{"domain": "example.org", "allowed": False}]
    assert not Registry.from_data(data).urls("iphone-14", "screen")


def test_missing_pairs_counted(data):
    assert len(Registry.from_data(data).unsourced_pairs) == 21


@pytest.mark.parametrize(
    "mutation", ["device", "issue", "duplicate", "url", "flag", "contradiction"]
)
def test_invalid_registry(data, mutation):
    device = data["devices"][0]
    repair = device["repairs"][0]
    source = repair["sources"][0]
    if mutation == "device":
        device["device_id"] = "iphone-99"
    elif mutation == "issue":
        repair["issue"] = "overheating"
    elif mutation == "duplicate":
        device["repairs"].append(copy.deepcopy(repair))
    elif mutation == "url":
        source["url"] = "file:///tmp/price"
    elif mutation == "flag":
        source["disabled"] = "false"
    else:
        repair["nothing_found"] = True
    with pytest.raises(ValueError):
        Registry.from_data(data)


def test_undefined_exclusion_shape_rejected(data):
    data["excluded_by_robots"] = [{"unknown": "format"}]
    with pytest.raises(ValueError):
        Registry.from_data(data)


@pytest.mark.parametrize(
    "data", [None, [], {}, {"devices": [None]}, {"devices": [{"device_id": "iphone-14"}]}]
)
def test_bad_structure(data):
    with pytest.raises(ValueError):
        Registry.from_data(data)


def test_invalid_json_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("not JSON")
    with pytest.raises(ValueError):
        Registry.load(path)


@pytest.mark.parametrize(
    "source_url,excluded",
    [
        ("https://EXAMPLE.org/repair/#source", "https://example.org/repair"),
        ("https://example.org/repair", "https://EXAMPLE.ORG/repair/#excluded"),
        ("https://example.org", "https://example.org/"),
    ],
)
def test_normalized_exclusions(data, source_url, excluded):
    data["devices"][0]["repairs"][0]["sources"][0]["url"] = source_url
    data["excluded_by_robots"] = [excluded]
    assert not Registry.from_data(data).urls("iphone-14", "screen")


@pytest.mark.parametrize(
    "excluded", ["https://example.org/Repair", "https://example.org/repair?variant=other"]
)
def test_meaningful_url_differences_preserved(data, excluded):
    data["excluded_by_robots"] = [excluded]
    assert Registry.from_data(data).urls("iphone-14", "screen")


def test_robots_exact_hostname(data):
    source = data["devices"][0]["repairs"][0]["sources"][0]
    source["url"] = "https://support.apple.com/repair"
    data["robots_txt"] = [{"domain": "apple.com", "allowed": False}]
    assert Registry.from_data(data).urls("iphone-14", "screen")
    data["robots_txt"].append({"domain": "SUPPORT.APPLE.COM", "allowed": False})
    assert not Registry.from_data(data).urls("iphone-14", "screen")


@pytest.mark.parametrize(
    "rules",
    [
        None,
        {},
        [None],
        [{}],
        [{"domain": "example.org"}],
        [{"domain": "example.org", "allow": False}],
        [{"domain": "example.org", "allowed": "false"}],
        [{"allowed": True}],
        [{"domain": "", "allowed": True}],
        [{"domain": "https://example.org", "allowed": True}],
        [{"domain": "example.org/path", "allowed": False}],
        [{"domain": 1, "allowed": False}],
    ],
)
def test_malformed_robots_rules(data, rules):
    data["robots_txt"] = rules
    with pytest.raises(ValueError):
        Registry.from_data(data)


@pytest.mark.parametrize(
    "url",
    [
        "https://user@host/x",
        "https://user:secret@host/x",
        "https://:secret@host/x",
        "https://@host/x",
        "https://:@host/x",
    ],
)
def test_credentials_rejected(data, url):
    from catalog_pipeline.registry import validate_url

    with pytest.raises(ValueError):
        validate_url(url)
    data["devices"][0]["repairs"][0]["sources"][0]["url"] = url
    with pytest.raises(ValueError):
        Registry.from_data(data)


@pytest.mark.parametrize("flag", ["disabled", "excluded"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("url", None),
        ("source_type", None),
        ("publisher", None),
        ("url", "file:///bad"),
        ("source_type", "unknown"),
        ("publisher", 12),
        ("note", []),
        ("requires_browser_ua", "true"),
    ],
)
def test_invalid_filtered_sources(data, flag, field, value):
    source = data["devices"][0]["repairs"][0]["sources"][0]
    source[flag] = True
    if value is None:
        del source[field]
    else:
        source[field] = value
    with pytest.raises(ValueError):
        Registry.from_data(data)


@pytest.mark.parametrize(
    "domain", ["[", "-bad.org", "bad_.org", "example.org:443", "*.example.org"]
)
def test_invalid_robots_hostname(data, domain):
    data["robots_txt"] = [{"domain": domain, "allowed": True}]
    with pytest.raises(ValueError):
        Registry.from_data(data)
