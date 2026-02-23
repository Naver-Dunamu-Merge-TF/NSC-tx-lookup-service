from __future__ import annotations

import pytest

from src.common import event_profiles


def test_load_event_profiles_requires_pyyaml(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    profile_file = tmp_path / "event_profiles.yaml"
    profile_file.write_text("version: 1\nprofiles: {}\n", encoding="utf-8")

    monkeypatch.setattr(event_profiles, "yaml", None)
    monkeypatch.setattr(
        event_profiles, "_yaml_import_error", ImportError("PyYAML missing")
    )
    event_profiles.clear_event_profiles_cache()
    try:
        with pytest.raises(RuntimeError, match="PyYAML"):
            event_profiles.load_event_profiles(profile_file)
    finally:
        event_profiles.clear_event_profiles_cache()
