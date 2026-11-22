"""File-based calendar text with regional and English fallbacks."""

import json
from pathlib import Path


def load_calendar_translations(directory: Path | None = None) -> dict[str, dict[str, str]]:
    """Read bundled translations in an executor, never during event rendering."""
    directory = directory or Path(__file__).parent / "calendar_translations"
    translations = {}
    for path in directory.glob("*.json"):
        labels = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(labels, dict) or not all(
            isinstance(value, str) and value.strip() for value in labels.values()
        ):
            raise ValueError(f"Invalid calendar translation: {path.name}")
        translations[path.stem.lower().replace("_", "-")] = labels
    if "en" not in translations:
        raise ValueError("English calendar translations are required")
    return translations


def calendar_labels(translations: dict[str, dict[str, str]], language: str) -> dict[str, str]:
    """Resolve exact language, then base language, then English, for each key."""
    language = (language or "en").lower().replace("_", "-")
    return {
        **translations["en"],
        **translations.get(language.split("-")[0], {}),
        **translations.get(language, {}),
    }
