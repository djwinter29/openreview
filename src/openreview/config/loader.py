"""! Functions for loading the openreview YAML configuration file."""

from __future__ import annotations

from pathlib import Path

import yaml

from openreview.config.schema import OpenReviewConfig


def load_config(path: Path) -> OpenReviewConfig:
    """! Load review configuration from disk.

    Missing files resolve to the default configuration.
    """

    if not path.exists():
        return OpenReviewConfig()
    raw = yaml.safe_load(path.read_text()) or {}
    return OpenReviewConfig.model_validate(raw)
