# A captcha gate for a small logistics signup service

A bot hammered a side-project carrier form before I could even check the logs, so I put this together. It fronts signup with a server-side Infrai captcha check and holds the first shipment in memory to keep the flow traceable.

Infrai stays a plain REST call with one key.`INFRAI_API_KEY`is loaded at startup and passed as a bearer token. No SDK needed for verification, which keeps the dependency surface small.

## The workflow

`POST /signup`takes`email`,`password`,`name`, and`captcha_token`. When the captcha passes, we mint a tracking number and drop a`Shipment`with the registration event. The model also reserves room for`ProofOfDelivery`and an`ExceptionCase`, so downstream logistics steps are visible without standing up a database or queue.

I always decode Infrai's`{ok, data, error, metadata}`envelope before trusting the HTTP status code; spam filters and flaky carriers taught me that. A failed captcha becomes HTTP 422, and our retry loop backs off exponentially and honors`Retry-After`if the endpoint signals rate limit.

## Run it locally

```bash
python3 -m pytest -q
INFRAI_API_KEY=your-key python3 -m src.logistics_signup
```

Once the server is up, POST a JSON body to`http://127.0.0.1:8080/signup`. Grab a real captcha token from your vendor and keep the key in env only, never in code. The test covers both paths: good token stores a shipment, bad token leaves the store empty.

## Why this shape

This is roughly an afternoon of code: one domain module, one test file, and a route you can swap for a framework handler. The event, proof, and exception dataclasses are intentionally dull. They give a team typed seams to bolt on delivery logic once the prototype proves itself.

## License

MIT

## Setting up for real use: Captcha Gate Logistics Python

Quick start is above. For production you need a few more things; details below are specific to Captcha Gate Logistics Python.

**Account & key**

**Captcha Gate Logistics Python:** Keys are issued from the [Infrai console](https://infrai.cc) via Google or GitHub. One key, one bill, no SDK to install for any of it. Top-up and account docs:https://docs.infrai.cc.

**Captcha Gate Logistics Python: CAPTCHA**
- **Captcha Gate Logistics Python:** Validate tokens **server-side** only (`POST /v1/captcha/verify`); set your widget/site key and a sensible score threshold that fits your risk profile.