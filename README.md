# IoT Device Simulator + Live Cloud Dashboard

A minimal end-to-end IoT pipeline, built entirely in software so it can
run on any laptop with no physical hardware. It mirrors the same
architecture a real IoT product uses:

```
[ Simulated Device ] --HTTP POST--> [ "Cloud" service ] --HTTP GET--> [ Dashboard ]
   publisher.py                        dashboard.py                browser (Chart.js)
```

## A note on the transport layer (read this first)

The original design for this project used **MQTT** to a public broker
(`broker.hivemq.com`) so `publisher.py` and `dashboard.py` never had to
know about each other directly -- that's how a real IoT deployment
works: devices publish to a broker, the cloud service subscribes,
fully decoupled. That is still the architecturally "correct" design
for a real product.

During testing, the outbound connection to the broker (on both port
1883 and the TLS port 8883) timed out consistently, even across two
different networks -- most likely local antivirus/firewall software
intercepting the connection. Rather than lose time fighting that,
this version swaps MQTT for a direct HTTP POST from the device to the
dashboard's `/api/ingest` endpoint, on the same machine. The pipeline's
*shape* is unchanged (device -> ingestion -> storage -> dashboard);
only the transport between device and cloud changed, from
publish/subscribe-over-MQTT to a direct HTTP call.

**This is worth mentioning in an interview, not hiding** -- it shows
you understand why MQTT is normally used (decoupling, designed for
constrained devices) and made a pragmatic call to unblock yourself
when the network environment didn't cooperate. That's a realistic
engineering trade-off, not a shortcut to be embarrassed about.

## Why this project, and what it demonstrates

| Real-world IoT concept          | What this project uses instead              |
|----------------------------------|----------------------------------------------|
| Physical sensor (temp/humidity/PIR) | `random`-generated values in `publisher.py` |
| Device firmware sending data     | `requests.post()` sending JSON               |
| MQTT broker (AWS IoT Core, etc.)| Direct HTTP call to `/api/ingest` (see note above) |
| Cloud ingestion service          | `dashboard.py`'s `/api/ingest` route         |
| Time-series database             | An in-memory `deque` (bounded, most recent N)|
| Dashboard / monitoring UI        | Flask + Chart.js, polling a JSON API         |
| Alerting on anomalies            | Console log on `motion_detected` (hook point for a real alert) |

The right column is a simplified stand-in for the left column. Swapping
the transport/storage layer for real MQTT + cloud services later would
not require changing the dashboard's core logic, just how data arrives
at `/api/ingest` vs. an MQTT subscriber.

## How to run it

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. In one terminal, start the dashboard (the "cloud" side) FIRST:
   ```
   python dashboard.py
   ```
   Then open http://127.0.0.1:5000 in your browser.
3. In a second terminal, start the simulated device:
   ```
   python publisher.py
   ```
4. Watch the dashboard update every ~2 seconds as new readings arrive.

## Design notes / talking points for interviews

- **Why MQTT is the "correct" choice for real devices (even though this
  version doesn't use it):** MQTT is a lightweight publish/subscribe
  protocol designed for constrained devices and unreliable networks --
  a device just publishes to a topic without needing to know who (if
  anyone) is listening. This decouples the device from the dashboard
  completely.
- **Why this version uses direct HTTP instead:** the MQTT broker
  connection was blocked in the testing environment (see note above).
  HTTP was used as a pragmatic fallback to get a working, demonstrable
  pipeline running -- the same lesson (understanding *why* a design
  choice matters, and adapting when the environment forces your hand)
  applies either way.
- **Why a bounded deque instead of an unbounded list?** Keeps memory
  usage predictable regardless of how long the publisher runs --
  mirrors how a real dashboard would only query a recent time window
  rather than loading an entire history into memory.
- **Why a lock around the deque?** Flask can handle multiple requests
  concurrently (e.g. `/api/ingest` and `/api/data` at the same time);
  without a lock, simultaneous read/write access to the same deque
  could corrupt it or raise an error.
- **Known limitation:** using an in-memory deque means data is lost if
  the dashboard restarts. A next step would be swapping this for a
  real database (SQLite to start, then a time-series DB) -- deliberately
  left as a clear "here's what I'd improve next" for this exact reason.

## Possible extensions

- Persist readings to SQLite instead of memory
- Add authentication to the MQTT connection using a private broker
- Trigger a real alert (email/Slack webhook) on `motion_detected`
  instead of just logging it
- Add a second simulated device and show both on the same dashboard
