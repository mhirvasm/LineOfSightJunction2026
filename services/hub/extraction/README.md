# Extraction boundary (C3/C4)

Not implemented in K0. The future interface is
`extract_receipt(image_bytes, mode)` as specified in `contracts/protocol.md`.
Only this module may produce a canonical receipt from the exact frozen image.
It must not select a target or invoke actions. Never fall back to fixture data
when a live request fails. Current UI samples are static JSON, not extraction.
