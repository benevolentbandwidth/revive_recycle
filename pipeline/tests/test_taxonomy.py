from pathlib import Path

import pytest

from catalog_pipeline.taxonomy import DEVICE_ISSUES, _load_mapping, validate_pair


def test_canonical_pilot_mapping():
    assert {key: len(value) for key, value in DEVICE_ISSUES.items()} == {
        "iphone-14": 7,
        "macbook-air-m2": 7,
        "surface-pro-9": 8,
    }
    validate_pair("iphone-14", "camera")
    validate_pair("surface-pro-9", "hinge-kickstand")
    with pytest.raises(ValueError):
        validate_pair("macbook-air-m2", "overheating")


@pytest.mark.parametrize("section", ["", "- malformed", "- **device** ? `screen`, `screen`"])
def test_malformed_mapping(tmp_path: Path, section):
    path = tmp_path / "S3.md"
    path.write_text(
        "**Device mapping (S2's three):**\n" + section + "\n**Naming rules:**", encoding="utf-8"
    )
    with pytest.raises(ValueError):
        _load_mapping(path)
