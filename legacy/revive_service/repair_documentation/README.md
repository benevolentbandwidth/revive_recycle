# iFixit repair documentation

This package searches the public iFixit API v2.0 for repair guides and ranks
them using deterministic device and issue keyword matching. It does not
estimate repair prices or make a Revive or Recycle recommendation.

```python
from revive_service.repair_documentation.ifixit_service import (
    get_repair_documentation,
)

result = get_repair_documentation(
    device="iPhone 12",
    issue="cracked screen",
)
```

By default, exact device-model guides are returned when available. Pass
`include_related_variants=True` to include related variants after exact
matches. If no exact guide exists, related variants are used as a fallback and
`used_related_variant_fallback` is set to `True`.

The client uses `GET /api/2.0/suggest/{query}?doctypes=guide` to search and
`GET /api/2.0/guides/{guideid}` to retrieve complete guide details.

Device normalization supports common aliases for iPhone, Samsung Galaxy,
Google Pixel, and OnePlus models. Canonical names for other iFixit-supported
devices, including tablets, laptops, and game consoles, can be searched
directly.

Deterministic issue matching covers screens, batteries, charging ports,
cameras, speakers, microphones, headphone jacks, power, liquid damage,
keyboards, trackpads, cooling, storage, joystick drift, and buttons. A guide
must still contain both the normalized device and issue terms to be returned.
