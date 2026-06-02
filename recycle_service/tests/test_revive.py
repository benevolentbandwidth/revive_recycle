"""
Basic tests for Revive service.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from src.services.revive_service import (
    condition_to_repair_key,
    normalize_condition,
)


def test_normalize_condition_screen():
    assert normalize_condition("screen cracked") == "cracked screen"
    assert normalize_condition("damaged display") == "cracked screen"


def test_normalize_condition_battery():
    assert normalize_condition("battery drains fast") == "battery issue"
    assert normalize_condition("bad battery") == "battery issue"


def test_normalize_condition_working():
    assert normalize_condition("works fine") == "works fine"
    assert normalize_condition("functional") == "works fine"


def test_normalize_condition_unknown():
    assert normalize_condition("water damage") == "unknown"


def test_condition_to_repair_key():
    assert condition_to_repair_key("cracked screen") == "screen"
    assert condition_to_repair_key("battery issue") == "battery"
    assert condition_to_repair_key("works fine") == "default"