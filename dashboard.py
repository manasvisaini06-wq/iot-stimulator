"""
dashboard.py
------------
Plays the role of "the cloud" in this mini IoT pipeline:
  1. Exposes an /api/ingest endpoint that publisher.py sends readings to.
  2. Keeps the most recent readings in memory (a real system would use a
     time-series database like InfluxDB or a cloud service like AWS IoT
     Core + DynamoDB -- this is the same idea, simplified).
  3. Serves a small web dashboard that polls a JSON API and redraws a
     live chart, so you can watch data arrive in real time.

NOTE ON THIS VERSION: the original design used an MQTT broker
(broker.hivemq.com) so publisher.py and dashboard.py never needed to
know about each other directly -- that's how a real IoT deployment
works (devices publish, the cloud subscribes, decoupled). That required
an outbound internet connection which got blocked during testing
(likely by local antivirus/firewall software). This version replaces
the MQTT broker with a direct HTTP endpoint on this same machine, so
the demo works reliably everywhere. The overall shape of the pipeline
(device -> ingestion -> storage -> dashboard) stays identical; only the
transport between device and cloud changed.

Run this file first, then run publisher.py in a separate terminal,
then open http://127.0.0.1:5000 in your browser.
"""

import threading
from collections import deque

from flask import Flask, jsonify, render_template_string, request

MAX_POINTS = 50  # how many recent readings to keep for the chart

app = Flask(__name__)

# A deque is used so old readings automatically drop off once we hit
# MAX_POINTS -- keeps memory bounded, similar to how a real dashboard
# would only query the last N minutes of data.
readings_lock = threading.Lock()
readings = deque(maxlen=MAX_POINTS)


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    """publisher.py POSTs one JSON reading here on every simulated tick."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    with readings_lock:
        readings.append(data)

    if data.get("motion_detected"):
        # This is the hook where you'd trigger a real alert
        # (email/Slack webhook/SMS) -- see alert_system.py for that piece.
        print(f"[ALERT] Motion detected by {data.get('device_id')} "
              f"at {data.get('timestamp')}")

    return jsonify({"status": "received"}), 200


@app.route("/api/data")
def api_data():
    """Returns the most recent readings as JSON, newest last."""
    with readings_lock:
        return jsonify(list(readings))


PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>IoT Sensor Dashboard</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
  <style>
    body { font-family: sans-serif; margin: 2rem; background: #111; color: #eee; }
    h1 { font-size: 1.3rem; }
    #status { color: #8f8; margin-bottom: 1rem; }
    canvas { max-width: 900px; }
    table { border-collapse: collapse; margin-top: 1.5rem; }
    td, th { border: 1px solid #444; padding: 4px 10px; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>Live IoT Sensor Dashboard (simulated device)</h1>
  <div id="status">Waiting for data...</div>
  <canvas id="chart" height="300"></canvas>
  <table id="log"><thead>
    <tr><th>Time</th><th>Temp (C)</th><th>Humidity (%)</th><th>Motion</th></tr>
  </thead><tbody></tbody></table>

<script>
const ctx = document.getElementById('chart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: { labels: [], datasets: [
    { label: 'Temperature (C)', data: [], borderColor: '#f66', tension: 0.3 },
    { label: 'Humidity (%)', data: [], borderColor: '#6cf', tension: 0.3 }
  ]},
  options: { animation: false, scales: { y: { beginAtZero: false } } }
});

async function poll() {
  const res = await fetch('/api/data');
  const data = await res.json();
  document.getElementById('status').innerText =
    data.length ? `Showing last ${data.length} readings` : 'Waiting for data...';

  chart.data.labels = data.map(d => d.timestamp.slice(11, 19));
  chart.data.datasets[0].data = data.map(d => d.temperature_c);
  chart.data.datasets[1].data = data.map(d => d.humidity_pct);
  chart.update();

  const tbody = document.querySelector('#log tbody');
  tbody.innerHTML = data.slice(-8).reverse().map(d =>
    `<tr><td>${d.timestamp.slice(11,19)}</td><td>${d.temperature_c}</td>` +
    `<td>${d.humidity_pct}</td><td>${d.motion_detected ? "YES" : "-"}</td></tr>`
  ).join('');
}

setInterval(poll, 2000);
poll();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
