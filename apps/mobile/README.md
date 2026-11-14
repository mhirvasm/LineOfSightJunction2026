# Native device work (iOS, phone first)

The selected first platform is iOS. No native integration exists yet. Android
is deferred. Build the Swift bridge on a suitable Mac and test the SDK with
MockDeviceKit, then stream an actual iPhone camera and use explicitly labelled
phone controls before integrating physical glasses and the Neural Band.

Follow the [phone-first development plan](../../docs/ios-phone-first-plan.md).
Keep Expenses and JSON in scope and destination selection menu-free. Phone and
mock checks do not pass the physical A1 gate. Before relying on glasses, prove
changing camera frames, display, and ten deliberate supported band selections
together, then record the actual hardware/SDK/OS/build results in
`docs/device-check.md`. Use the installed SDK's documented APIs.
