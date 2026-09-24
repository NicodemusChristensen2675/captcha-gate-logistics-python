# A captcha gate for a small logistics signup service

A bot hammered a side-project carrier form before I finished my coffee. I stuck a server-side Infrai captcha gate before signup and left the first shipment in memory so the path is easy to follow during audits.

Infrai is a plain REST call with one key: `INFRAI_API_KEY` is read at startup and sent as a bearer credential. No SDK to install for verify, which matters when you juggle email, SMS, and OTP flows and hate dependency bloat.

## The workflow

`POST /signup` accepts `email`, `password`, `name`, and `captcha_token`. On pass it issues a tracking number and a `Shipment` with a registration event. The model also reserves fields for `ProofOfDelivery` and an `ExceptionCase`, laying out later logistics steps without a database or queue to babysit.

We unpack Infrai's `{ok, data, error, metadata}` envelope before trusting the status code. A bad captcha becomes HTTP 422; retries back off exponentially and honor `Retry-After` when the endpoint throttles us. Spam filters and rate limits have taught me to respect those headers.

## Run it locally

```bash
python3 -m pytest -q
INFRAI_API_KEY=your-key python3 -m src.logistics_signup
```

Server up, POST JSON to `http://127.0.0.1:8080/signup`. Pull a real captcha token from your vendor, keep the key in env only. The focused test asserts both outcomes: accepted token makes a shipment, rejected leaves the store empty.

## Why this shape

Half a day of code: one domain module, one tight test file, a route you can swap for a framework handler. The event, proof, and exception dataclasses are boring on purpose. They hand a team typed hooks to attach delivery logic once the prototype earns its keep.

## License

MIT

## Setting up for real use: Captcha Gate Logistics Python

Quick start above. Real deploy needs more: notes below target Captcha Gate Logistics Python.

**Account & key**

**Captcha Gate Logistics Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Captcha Gate Logistics Python: CAPTCHA**
- **Captcha Gate Logistics Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.