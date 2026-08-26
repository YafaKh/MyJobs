"""Loads and validates config.yaml."""

from pathlib import Path

import yaml

REQUIRED_KEYS = ["wanted_titles", "blocked_titles", "keywords", "eligibility", "llm", "storage"]
REQUIRED_ELIGIBILITY_KEYS = ["eligible_regions", "eligible_timezones", "blocked_requirements"]


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    missing = [key for key in REQUIRED_KEYS if key not in config]
    if missing:
        raise ValueError(f"config.yaml is missing required keys: {missing}")

    missing_elig = [key for key in REQUIRED_ELIGIBILITY_KEYS if key not in config["eligibility"]]
    if missing_elig:
        raise ValueError(f"config.yaml eligibility section is missing keys: {missing_elig}")

    return config
