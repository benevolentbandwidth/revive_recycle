# Development Setup

## Getting your API keys

This is the first thing to do after cloning the repo. The target build depends on a handful of external services, and each one needs a local environment variable.

> Keep all keys in a local `.env` file and do not commit them to git.

### Overview

| Service | What it's for | Do you need a key? |
|---|---|---|
| [SoldComps](#soldcomps) | Sold eBay prices | Yes |
| [InferX (DeepSeek)](#inferx-deepseek) | The AI model via InferX's hosted `deepseek-v4-flash-0731` endpoint | Yes |
| [Google Places API](#google-places-api) | Nearby repair shops and recycling centers | Yes |
| [iFixit](#ifixit) | Repair guides | No |

Use your own API keys while the app is being developed locally.

Once you have your keys, copy the root [`.env.example`](../.env.example) to `.env`
(it's already gitignored) and fill them in there for your own reference.

None of these ever go in `web/`. The frontend is a static export, so anything in
`web/.env.example` is compiled straight into JavaScript the browser downloads —
it's public by design.

**`.env` is a local-dev-only convention — production keys don't live there.** In
the deployed system:

- The **pipeline** (GitHub Actions, monthly) reads its InferX/DeepSeek key from a
  **GitHub Actions secret**.
- The **Market Data Service** (the standalone Cloud Function) reads its SoldComps,
  Google Places, and InferX/DeepSeek keys from **its own server-side config**
  (a Cloud Function secret), not from a `.env` file and not from GitHub Actions.

Both need their own copy of the InferX/DeepSeek key provisioned separately — it's
one key from InferX, but two secrets to set up.

### SoldComps

1. Go to https://sold-comps.com/ and create a free account.
2. An API key is issued immediately when you sign up. Keys start with `sc_`
3. Add it to your local `.env` file as `SOLDCOMPS_API_KEY`.

The free (Basic) tier is **100 requests per month**, at up to 60 requests/minute. A single working device variant lookup (and its broken counterpart) are two separate SoldComps requests, so **one full end-to-end test run of the app (the kind that
misses the cache and has to hit SoldComps live) costs 2 requests**. That
gives you **about 50 full test runs a month** on the free tier before you're out
until next month's reset.

Cached reads don't count against this — a repeat lookup for the same
device/condition/variant within 30 days is served from Firestore and makes zero
SoldComps requests. Budget manual testing accordingly: exercise the cache path freely, and reserve live runs for when you actually need to verify the SoldComps integration itself.

See [SoldComps API docs](https://sold-comps.com/docs).

### InferX (DeepSeek)

1. Go to https://inferx.net/ and click "Start Building."
2. Sign in with your GitHub or Google account.
3. An API key is issued immediately after account creation.
4. Copy that key into your local `.env` file as `INFERX_API_KEY`.

See [InferX Help](https://model.inferx.net/help) for more information.

### Google Places API

1. Go to https://console.cloud.google.com/ and sign in, or create a Google account if needed.
2. Create a new project, or reuse a personal sandbox project, and make sure it has a
   **billing account attached** — Google requires one to enable or call Places API
   (New) even while you're within the free usage tier.
3. Open **APIs & Services → Library**, search for **Places API (New)**, and enable it.
4. Open **APIs & Services → Credentials → Create Credentials → API key**.
5. Give it a name and restrict the key immediately: click into it and under **API restrictions** limit
   it to **Places API (New)**.
6. Save the key in your local `.env` file as `GOOGLE_PLACES_API_KEY`.

See [Google Places API documentation](https://developers.google.com/maps/documentation/places/web-service/overview).

### iFixit

iFixit's public API does not require a key or account for the read-only endpoints used here, so there is no `.env` key to add for iFixit.

See [iFixit API docs](https://www.ifixit.com/api-docs) for more information.

## Testing your API keys

See some test commands and scripts below to verify your personal API keys.

**SoldComps**

Terminal:
```bash
curl -H "Authorization: Bearer $SOLDCOMPS_API_KEY" "https://api.sold-comps.com/v1/scrape?keyword=iphone+15+pro"
```

**InferX**

Terminal:
```bash
pip install openai
```

Python:
```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["INFERX_API_KEY"],
    base_url="https://model.inferx.net/endpoints/v1",
)

stream = client.chat.completions.create(
    model="deepseek-v4-flash-0731",
    messages=[{"role": "user", "content": "Hello, InferX."}],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")
```

**Google Places API**

Terminal (from project root):
```bash
cd legacy/recycle_service
python -m tests.test_google_places
```

**iFixit**

Terminal:
```bash
curl "https://www.ifixit.com/api/2.0/suggest/iphone%2012?doctypes=guide"
```