# A1: actual device and network checks

Demo: 15 November 2026, 10:00 Europe/Helsinki (team-reported).
Estimated working time when bootstrap began: 16-20 hours, allowing for sleep.

| Item | Status / value |
| --- | --- |
| Integration human | `mhirvasm` (K0 issue owner) |
| Device human | To be assigned |
| Screens / presentation human | To be assigned |
| Glasses / band access | Not yet available when bootstrap began |
| Available computers | Two Macs, Lenovo ThinkPad |
| Available phones | iPhone, Samsung Galaxy S23 |
| Selected native platform | Undecided; confirm with booth |
| Next hardware slot | To be confirmed with booth |
| Hub IP / private network | Not tested / to be recorded |
| Phone-browser health check | NOT TESTED |
| Second-computer health check | NOT TESTED |
| Live glasses camera frames | NOT TESTED |
| Display rendering | NOT TESTED |
| Ten deliberate supported band/button callbacks | NOT TESTED |
| Camera + display + input in the same session | NOT TESTED |
| Remove/re-wear and resume | NOT TESTED |
| SDK / firmware / phone OS / build command | Record actual values after test |
| Known-good hardware build / commit | None yet |

Android bridge follow-up (14 November 2026): the separately requested
`feat/android-sdk-bridge` task uses DAT 1.0.1. Its debug APK, nine native JVM
tests, and lint pass. Actual phone-camera and glasses/band checks remain
pending; the S23 did not enumerate in Windows/ADB during the first USB attempt.
See [task #6](tasks/A2-A3-android-sdk-bridge.md) for software evidence and the
phone test runbook. iOS planning remains separate.

Start by asking Amanda/the Meta booth which paired phone, account, firmware,
and official sample work with the loaned Display glasses and Neural Band.
Use that sample's documented APIs. Prove changing upright live frames and
ten deliberate supported callbacks together before A2. Local browser or
simulator success cannot pass this gate.

Before the slot, use README's network check with both target pages visible,
print the synthetic receipt, bring chargers and a data cable, and record one
specific hardware question. No native app exists in this milestone.
