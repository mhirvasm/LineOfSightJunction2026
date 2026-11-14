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
| Selected native platform | iOS first; phone/mock tests before glasses; Android deferred |
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

The selected development sequence is recorded in the
[iOS phone-first plan](ios-phone-first-plan.md). The platform decision does not
change any untested hardware result above. Mock SDK and physical iPhone camera
results must be recorded separately from real glasses/band results.

Start by asking Amanda/the Meta booth which paired phone, account, firmware,
and official sample work with the loaned Display glasses and Neural Band.
Use that sample's documented APIs. Prove changing upright live frames and
ten deliberate supported callbacks together before A2. Local browser or
simulator success cannot pass this gate.

Before the slot, use README's network check with both target pages visible,
print the synthetic receipt, bring chargers and a data cable, and record one
specific hardware question. No native app exists in this milestone.
