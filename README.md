# Shahaf Timetable for Home Assistant

<img src="custom_components/shahaf/brand/icon.png" alt="Shahaf Timetable app icon" width="96" height="96">

Unofficial integration for **שחף מערכת שעות**, the Android app
`com.shahafsoft.timetableapp`. Connect directly to Shahaf with the app's student
login. A connected phone is only needed for development research, not normal use.

## Install

Requires Home Assistant **2026.2 or newer**. Setup is available in English and Hebrew.

### Marketplace (Home Assistant 2026.11 and newer)

[Open Shahaf in your Marketplace](https://my.home-assistant.io/redirect/marketplace_repository/?owner=NirBY&repository=ha-shahaf&category=integration)

Open **Settings → Marketplace → Add from link** and enter
`https://github.com/NirBY/ha-shahaf`. Select **Add**, then **Install**. Connect
GitHub if prompted. Marketplace opens the integration setup after installation,
or tells you if a restart is required.

Marketplace replaces HACS in Home Assistant 2026.11 and supports the same
repository format. See the [official Marketplace guide](https://www.home-assistant.io/integrations/marketplace/).

### HACS custom repository (older Home Assistant versions)

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/NirBY/ha-shahaf`, category **Integration**.
3. Download **Shahaf Timetable** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Shahaf Timetable**.
5. Enter the school ID (סמל מוסד), username and password. Select the campus and
   class, and optionally give it a label such as the child's name.

This repository supports HACS custom installation. It is not yet included in
HACS's default searchable catalog. Default-catalog inclusion needs a separate
submission and review. The integration includes its own brand images, which
satisfy the HACS Brands check without a separate Brands repository submission.

### Manual installation

Copy the `custom_components/shahaf` directory to
`/config/custom_components/shahaf`, restart Home Assistant, then follow steps 4–5.
The release ZIP contains `custom_components/shahaf` and can be extracted into
the Home Assistant configuration directory. HACS itself is optional.

Add the integration again for each additional class. Existing classes are
detected to prevent duplicate entities. Upgrades preserve configuration and
entity IDs; replace only the integration directory and restart Home Assistant.

## Entities

### Calendars

Each class provides separate **Timetable**, **Changes**, and **Events** calendars.
Changes contains only published schedule changes, including cancellations and
substitutions, with period numbers and the full notice text. Events contains exams
and school events. Select Changes alone on a family dashboard to exclude normal
lessons and the separate events feed.

The combined **All data** calendar remains available for existing dashboards.

Calendar category labels follow Home Assistant's configured language: English
or Hebrew, including Updates / עדכונים, Events / אירועים and Changes / שינויים.
School-provided text and student names remain exactly as published. Unsupported
languages fall back to English; regional variants fall back to their base language.
All data combines timed lessons, exams, events, schedule changes (including the
school's cancellation text), and dated notices. Period numbers and the full
original text are retained in descriptions. Lessons without bell times appear
as all-day entries in All data. Undated notices are included in event descriptions,
without assigning them an invented date. Only published dates are shown.

The calendars appear automatically in Home Assistant's **Calendar** sidebar.
Select the desired calendars there. For a dashboard, edit a Calendar card and
add each class's desired calendar entity; use the entity picker because names depend
on your labels. Choose All data alone to avoid duplicating the separate calendars.

### Cancellation alerts (GreenAPI blueprint)

[Import the cancellation blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2FNirBY%2Fha-shahaf%2Fmain%2Fblueprints%2Fautomation%2Fshahaf%2Fcancellation_greenapi.yaml).
Create one automation per class, select its **Schedule changes** sensor, enter
a class/child label and an international WhatsApp number (digits only), and use
your existing GreenAPI notification action (default `notify.greenapi`). Credentials
stay in that notifier's configuration. The integration does not configure GreenAPI.

The blueprint sends newly added or changed explicit Hebrew cancellation notices
for today or later. Messages include the date, periods and original school text;
parallel groups are not assumed to apply to every student. Unchanged refreshes
do not resend messages. Startup establishes a baseline, so this example does not
backfill cancellations published while HA was stopped. A changed or removed and
later republished notice can send another alert. Detection follows the configured
refresh interval (15 minutes by default). Delivery depends on GreenAPI connectivity.

Each configured class creates:

| Entity | Contents |
| --- | --- |
| Published timetable sensor | Number of published slots; dated `schedule` attribute for the current and following week |
| Today / Tomorrow sensors | Slot counts and complete `lessons`, including teacher, room and change text |
| Schedule changes sensor | Dated replacement, cancellation and other notices as published by the school |
| Exams / Events / Notices sensors | Published entries with dates and original text |
| Lessons calendar | Timed slots, including all parallel subjects and published notes |
| Events calendar | Exams and events; matched timetable times when available, otherwise all-day |
| All data calendar | Lessons, changes, exams, events and dated notices; undated notices in descriptions |
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
School events and changes use timetable start/end times when one explicit period
range can be matched completely to that class on the same date. Explicitly all-day
events, missing times, and ambiguous ranges stay all-day; no times are invented.
Original period information is kept in the description. Multiple events grouped by Shahaf on one day remain
together. An exam may appear under **Events** if the school publishes it there.

The first version understands the Hebrew presentation format currently returned
by the app. Unknown timetable layouts fail visibly instead of silently becoming
an empty timetable. The upstream API is unofficial and may change.

## Adding languages

Copy `custom_components/shahaf/calendar_translations/en.json` to `<language>.json`
in the same folder and translate its values, keeping the keys. No calendar logic
changes are needed. Missing translated keys fall back to English. For translated
setup forms and entity names, also copy and translate `translations/en.json`
using Home Assistant's translation format. Restart after adding translation files.
Event text uses the server language, so all users receive the same event titles;
school-provided content is not automatically translated.

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
and the local event-loop socket pair. Linux CI runs the unmodified Home Assistant
test framework. Tests use fictional data.

The GitHub workflow also runs Hassfest and all HACS validation checks, including
Brands.

## App icon

The original icon from the [Shahaf Android app on Google Play](https://play.google.com/store/apps/details?id=com.shahafsoft.timetableapp)
is bundled in `custom_components/shahaf/brand` at 256 and 512 pixels. It belongs
to Shahaf Educational Information Systems Ltd and is used to identify the service;
the integration's MIT license does not grant rights to Shahaf's trademarks or artwork.
Home Assistant **2026.3 and newer** displays these local brand images. Earlier
supported versions can still use the integration but may show a placeholder icon.
See [Home Assistant's local brand image support](https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/).

Not affiliated with or endorsed by Shahaf or the Ministry of Education.
