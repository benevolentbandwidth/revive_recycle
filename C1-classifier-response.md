# C1 (#88) — Decide what the AI has to return

The Symptom Classifier returns this JSON object.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `device_id` | string | yes | Echoed back from the device already selected on the Landing screen. Not classified — see Reasoning. |
| `condition` | `"working"` \| `"broken"` | yes | Normalized device condition. |
| `variant` | string **or `null`** | yes | The device's spec tier, e.g. `"128gb"`. `"base"` when the device has no variant axis. **`null` means "could not be determined"** |
| `issues` | object | yes | Map of S3 problem-tag id → probability. Keys restricted to the S3 taxonomy. Tags with probability 0 are omitted. |
| `confidence` | number, 0–1 | yes | Confidence in `issues` only (see below). |

No other top-level fields. No joined `{device_id}__{condition}__{variant}` key, the model
emits the three components separately, per invariant 2; the Market Data Service composes
the key.

### `issues`

- Keys: the ten S3 tag ids — `screen`, `battery`, `wont-power-on`, `water-damage`,
  `charging-port`, `speaker`, `camera`, `keyboard-trackpad`, `hinge-kickstand`,
  `overheating`. Any other key is a schema violation, an invented tag is invalid.
- Values: independent per-tag probabilities, `0`–`1`. **Not a categorical distribution —
  they are not required to sum to 1.** Multiple tags can be simultaneously high (a
  `water-damage` report could raise `screen`, `battery`, `speaker`, and
  `charging-port`).
- A tag not present in the object is implicitly `0`.
- **Schema-level validity is not device-level validity.** This schema only knows the ten global
  tag ids, doesn't know that `keyboard-trackpad` is meaningless for `iphone-14` because
  that mapping lives in the device catalog. **M12 must additionally reject any tag the specific 
  `device_id`'s catalog entry doesn't list** even though it passes this schema. This mirrors the 
  existing split between S8 (shape) and P7 (sanity), format and plausibility are checked in different places.

### `confidence`

- Range `0`–`1`. Meaning: **how confident the model is that the `issues` probabilities are
  complete and correct enough to act on without asking the user anything further.**
- This document does not set the number below which a follow-up question fires, that's
  C6, measured against C2's test set. Its a configurable setting not a constant baked in here.
- Applies only to `issues`.

### `variant`

- One of the device's `variant_key_field` options (catalog-defined, e.g. `128gb`, `256gb`),
  in the same lowercase-kebab form as the catalog; or the literal `"base"` for a device
  with no variant axis; or **`null`**.
- `null` is the *only* correct output when the variant can't be determined for a device
  that has one. This can happen even when `issues`/`confidence` are high — a description
  can be completely clear about a cracked screen while saying nothing about storage. C7
  needs to detect and signal that case independently of symptom confidence, and this
  schema gives it a direct, type-level way to do so: no numeric threshold to get right, no
  guessed value that a careless caller could accidentally use.
- **Never a guessed value.** A wrong guess here writes a wrong price into the 30-day shared
  market cache, and every other user asking about that device for the next month
  reads the same wrong number. `null` forces the clarification path instead.
- A `base` device (no `variant_key_field`) must never emit `null`, there is nothing to be
  unsure about, and C7 must never trigger a storage question for it.

### `device_id` and `condition`

Both are **normalization not classification.** The user picks their device on the Landing
screen before this call ever fires — the prompt (C4) receives the known device
record from the catalog alongside the form input. The model's job on these two fields is
to echo them back in canonical form as part of the atomic three-value lookup key.

Consequently:
- **M12 must hard-reject** a response whose `device_id` doesn't exactly match the device_id
  sent in the request. This is a validation failure not a low-confidence case.
- `condition` keeps both enum values for schema completeness and because the Market Data
  Service's key shape treats `condition` as a first-class axis independent of this
  classifier. But the self-diagnosis flow only ever describes a device the user has
  reported as broken, so in v1 this field will always resolve to `"broken"`. Nothing in
  the flow currently produces `"working"` from this endpoint.

## Examples

**Clear description resolved variant** — "iphone 14 128GB cracked display":

```json
{
  "device_id": "iphone-14",
  "condition": "broken",
  "variant": "128gb",
  "issues": { "screen": 0.94, "wont-power-on": 0.04 },
  "confidence": 0.91
}
```

**Confident on symptoms, storage never mentioned** — "my macbook air screen is cracked":

```json
{
  "device_id": "macbook-air-m2",
  "condition": "broken",
  "variant": null,
  "issues": { "screen": 0.9 },
  "confidence": 0.88
}
```

`confidence` is high — the model is not unsure about the symptom. `variant` is `null`
regardless, and that alone is what should trigger C7's storage question; it must not be
conflated with a low `confidence` reading.

**Genuinely vague** — "it just stopped working idk":

```json
{
  "device_id": "surface-pro-9",
  "condition": "broken",
  "variant": "256gb",
  "issues": { "wont-power-on": 0.4, "battery": 0.3, "charging-port": 0.2 },
  "confidence": 0.35
}
```

Low `confidence` here should trigger the generic symptom clarification, independent
of the fact that `variant` happened to resolve fine.

## Machine-readable schema

[`schemas/classifier-response.schema.json`](schemas/classifier-response.schema.json) — JSON
Schema Draft 7 (chosen for the widest validator support across languages/tooling; nothing
in it depends on later-draft features, so M12 can swap drafts freely if its stack prefers
one). Validates shape and the global tag enum only, per the split described above — it does
not and cannot check per-device tag applicability, which needs the loaded catalog at
request time.

## Reasoning

**Why a nullable `variant` instead of a per-field confidence score for everything.** C7
(#94) requires detecting "we don't know the storage size" as a signal *independent* of
symptom confidence, triggered "even when the symptom diagnosis was confident," and states
as a hard requirement that **no code path may guess a storage size.** A parallel
`variant_confidence` number next to an always-populated best-guess `variant` would satisfy
the letter of that but not the spirit: it relies on every future caller remembering to
check the confidence before using the value. `null` makes the unresolved state
unrepresentable as a usable value — you cannot accidentally build a cache key or a price
lookup out of `null`. Given invariant 4 (one SoldComps request per figure) and the fact that 
a bad variant corrupts a shared 30-day cache entry for everyone, the stronger guarantee is 
worth it. `confidence` stays scoped to `issues`, which is the one field that's genuinely a 
probability distribution rather than a resolved-or-not lookup value.

**Why `issues` omits zero-probability tags instead of listing all applicable ones.** Kept
the response minimal and lets C4's prompt focus on producing tags it actually detected
rather than exhaustively scoring ones it didn't. If C3's scoring tool later needs to
distinguish "ruled out" from "never evaluated," that's a C3/C8 concern to revisit against
real measured behavior.

**Why `device_id`/`condition` aren't treated as classification targets.** Every downstream
issue that discusses uncertainty (C6, C7) talks about symptom confidence and storage/variant 
resolution, never about the device or its condition being unclear. That's consistent with the 
flow: device is picked explicitly before this call fires, and condition is fixed by the fact 
that this whole flow is to diagnose a device the user says is broken. Treating them as 
passthrough-with-hard-validation (rather than probabilistic) keeps the schema's two real 
uncertainty surfaces — `issues`/`confidence` and `variant` — the two things the prompt (C4) 
and the test set (C2) need to reason about.

**Why the tag enum is global rather than dynamically scoped per device.** The JSON Schema is
static; it can't vary its own `enum` based on which `device_id` happens to be in the same
document without a schema-per-device (or a schema compiled at request time from the
catalog), either of adds complexity for a project designed to need minimal maintenance. 
The global enum still satisfies C1's requirements — an invented tag is invalid — and the 
narrower per-device check is pushed to M12, which has the catalog loaded to do it. Same 
shape-vs-plausibility split the project already uses for S8 (file shape) versus P7 (sanity band).

**Why `schemas/` instead of root-level.** `S2-choose-3-devices.md` and
`S3-failure-taxonomy.md` the issue-answer docs already live at repo root, which
this follows for `C1-classifier-response.md`. The JSON Schema is a different kind of
artifact meant to be `require()`d/loaded by code (M12), so it goes in a new `schemas/` directory 
rather than cluttering root with raw JSON. S8 ("write a JSON Schema for both [catalog] files") 
is about to need this kind of file for two more documents. This establishes the folder.
