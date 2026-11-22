# Shahaf Timetable for Home Assistant

Unofficial integration for **שחף מערכת שעות**, the Android app
`com.shahafsoft.timetableapp`. Connect directly to Shahaf with the app's student
login. A connected phone is only needed for development research, not normal use.

## Install

Requires Home Assistant **2026.2 or newer**. Setup is available in English and Hebrew.

### HACS custom repository

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/NirBY/ha-shahaf`, category **Integration**.
3. Download **Shahaf Timetable** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Shahaf Timetable**.
5. Enter the school ID (סמל מוסד), username and password. Select the campus and
   class, and optionally give it a label such as the child's name.

This repository supports HACS custom installation. It is not yet included in
HACS's default searchable catalog. Default-catalog inclusion needs a separate
submission, including a Home Assistant Brands entry.

### Manual installation

Copy the `custom_components/shahaf` directory to
`/config/custom_components/shahaf`, restart Home Assistant, then follow steps 4–5.
The release ZIP contains `custom_components/shahaf` and can be extracted into
the Home Assistant configuration directory. HACS itself is optional.

Add the integration again for each additional class. Existing classes are
detected to prevent duplicate entities. Upgrades preserve configuration and
entity IDs; replace only the integration directory and restart Home Assistant.

## Entities

Each configured class creates:

| Entity | Contents |
| --- | --- |
| Published timetable sensor | Number of published slots; dated `schedule` attribute for the current and following week |
| Today / Tomorrow sensors | Slot counts and complete `lessons`, including teacher, room and change text |
| Schedule changes sensor | Dated replacement, cancellation and other notices as published by the school |
| Exams / Events / Notices sensors | Published entries with dates and original text |
| Lessons calendar | Timed slots, including all parallel subjects and published notes |
| School events calendar | All-day entries preserving the school's event text and period information |
| Last refresh sensor / Refresh button | Data freshness and manual refresh |

The default refresh interval is **15 minutes**. Change it under the integration's
**Configure** menu (5–1440 minutes). Date-dependent values advance every minute
without making additional API calls. All school dates and times use
**Asia/Jerusalem**, including daylight-saving time.

When a connection fails, entities become unavailable and retain their last
successful attributes with `data_stale: true`. A failed request is never treated
as an empty school day. Invalid credentials open Home Assistant's reauthentication
flow. An unpublished date has an unknown count, rather than a fabricated zero.

## What the data means

Shahaf provides a **class timetable**, including parallel teaching groups. The
integration does not know which group a particular student attends. It preserves
the school's displayed subjects and notes, including changes and substitutions.
It does not infer that a notice cancels every parallel group in a time slot.

Only returned dates are exposed: lessons are not repeated into future weeks.
Missing bell times remain missing and are omitted from the timed calendar.
School events use all-day calendar entries; their original period information is
kept in the description. Multiple events grouped by Shahaf on one day remain
together. An exam may appear under **Events** if the school publishes it there.

The first version understands the Hebrew presentation format currently returned
by the app. Unknown timetable layouts fail visibly instead of silently becoming
an empty timetable. The upstream API is unofficial and may change.

## Future Mashov integration

This integration is independent of `ha-mashov`; installing it does not change
Mashov entities or dashboards. The `schedule` attribute provides a stable,
versioned input for a future merge:

```json
{
  "schema_version": 1,
  "school_id": "123456",
  "campus_code": 1,
  "class_id": 6,
  "class_name": "ז - 6",
  "scope": "class",
  "data_stale": false,
  "schedule": [{
    "date": "2026-11-22",
    "day": 1,
    "lessons": [{
      "lesson": 1,
      "subject": "Math / English",
      "start": "2026-11-22T08:30:00+02:00",
      "end": "2026-11-22T09:15:00+02:00"
    }]
  }]
}
```

`day` is 1=Sunday through 7=Saturday. `class_id` is Shahaf's internal identifier,
**not** `grade * 100 + class number`. Match the ministry school ID, campus and
class name before joining data. Use the full ISO `date` and freshness metadata;
do not substitute the entire class schedule for a student's selected groups.

## Credentials and development

Credentials live in Home Assistant's config entry. Session tokens stay in memory.
Diagnostics contain counts and timestamps only, with no credentials, child names
or lesson text. The integration does not log credential-bearing URLs, register
phone notifications, or modify school data.

```console
pip install -r requirements-dev.txt
pytest -q
ruff check custom_components tests run_tests.py
```

On Windows use `python run_tests.py -q`; it adapts Unix-only test-framework imports
and the local event-loop socket pair, as in the existing Mashov project. Linux CI
runs the unmodified Home Assistant test framework. Tests use fictional data.

The GitHub workflow also runs Hassfest and HACS validation. HACS's Brands check is
excluded until a separate brand submission is made.

Not affiliated with or endorsed by Shahaf or the Ministry of Education.
