# Capture extraction

ContentReader reads the exact frozen JPEG once and returns text plus an optional
validated receipt. ReceiptReader supplies the shared Gemini/OpenAI transport and
retains the narrow receipt interface for compatibility checks. Neither reader
chooses a destination or performs a transfer.

The hub uses ContentReader. Live mode sends the image to the explicitly selected
provider; keys stay in the ignored local configuration. There is no provider or
fixture fallback. Receipt validation only enables the Expenses/receipt-JSON output;
a readable note can still reach Text or text JSON. Text is bounded to 8000
characters and rendered literally. See contracts/protocol.md for the payloads.

Fixture mode is explicit and labelled. LOS_FIXTURE_CONTENT selects receipt or
text synthetic data; fixtures do not read pixels. Run scripts/verify_live_text.py
and scripts/verify_live_receipts.py for paid live checks with synthetic images.
Physical handwriting, camera readability and glasses HUD checks remain separate.

TextAnalyzer adds a second request only when no validated receipt is present.
It sends text only to the same configured provider and returns corrected_text
and a short summary. Keep raw_text unchanged; validate numeric/URL tokens and
uncertainty markers as well as field lengths. This cannot prove semantic accuracy.
On a failed or timed-out analysis, retain the original transcription and mark
text_status=unavailable. Cancellation guards cover both phases; never revive a
canceled capture. Receipts bypass analysis, and Coffee actions invoke neither
reader. Run scripts/verify_live_analysis.py for the paid synthetic grammar and
negation checks. The analysis fixture applies only to its exact synthetic source.
