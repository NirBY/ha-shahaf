# Version 0.1.0 validation

Verified on 22 November 2026.

## First install and initialization

- Passed the complete Home Assistant setup flow: credentials → campus → class.
- Created two distinct class entries on Home Assistant 2026.11.2.
- Both entries reached `loaded`, with 22 registered entities in total.
- Verified configuration before the initial Home Assistant restart.
- Verified the options flow, reload and unchanged entity IDs.
- Retrieved the lesson calendars through Home Assistant's calendar API.
- Verified manual refresh and fresh state attributes.
- Confirmed all 97 pre-existing Mashov entities remained present.

## Automated checks

16 tests passed against Home Assistant 2026.2.3 with the Windows test launcher.
Coverage includes the full setup and reload lifecycle, duplicate classes,
credential recovery, transport failure handling, session renewal, exact API
routes, calendar boundaries, parallel groups, missing times, year boundaries,
and Israel daylight-saving offsets. Ruff and Python compilation passed.

Linux tests, Hassfest and HACS checks are configured in the GitHub workflow.
Their results must be checked after publication. Default HACS catalog inclusion
and a Home Assistant Brands entry are not part of this release.

## Data and privacy checks

The live client independently authenticated two class sessions and retrieved
the current and following week's data. No phone is required at runtime.
Public files were checked for the supplied credentials, access token, private
server address, and live school identifier; none are included. Tests contain
fictional data. APKs, analysis output, access tokens and live responses remain
in the ignored local research directory and are excluded from release ZIPs.
