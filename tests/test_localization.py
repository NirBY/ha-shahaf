import json

from custom_components.shahaf.localization import calendar_labels, load_calendar_translations


def test_new_language_files_and_per_key_fallback(tmp_path):
    (tmp_path / "en.json").write_text(json.dumps({"events": "Events", "changes": "Changes"}))
    (tmp_path / "fr.json").write_text(json.dumps({"events": "Événements"}))
    (tmp_path / "fr-CA.json").write_text(json.dumps({"changes": "Modifications"}))
    translations = load_calendar_translations(tmp_path)
    assert calendar_labels(translations, "fr") == {"events": "Événements", "changes": "Changes"}
    assert calendar_labels(translations, "fr_CA") == {
        "events": "Événements",
        "changes": "Modifications",
    }
    assert calendar_labels(translations, "unknown") == translations["en"]


def test_bundled_calendar_translations_have_all_english_keys():
    translations = load_calendar_translations()
    for labels in translations.values():
        assert labels.keys() == translations["en"].keys()
