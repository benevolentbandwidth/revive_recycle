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
