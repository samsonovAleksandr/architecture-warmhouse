import json
import random
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse


PORT = 8081

LOCATIONS = {
    "1": "Living Room",
    "2": "Bedroom",
    "3": "Kitchen",
}

SENSOR_IDS = {
    location: sensor_id
    for sensor_id, location in LOCATIONS.items()
}

last_temperatures = {}
temperature_lock = threading.Lock()


def generate_temperature(sensor_id):
    with temperature_lock:
        previous = last_temperatures.get(sensor_id)

        candidates = [
            value
            for value in range(180, 301)
            if value != previous
        ]

        value = random.choice(candidates)
        last_temperatures[sensor_id] = value

        return value / 10


class TemperatureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        params = parse_qs(url.query, keep_blank_values=True)

        location = params.get("location", [""])[0].strip()
        sensor_id = params.get(
            "sensorId",
            params.get("sensor_id", [""]),
        )[0].strip()

        if url.path == "/temperature":
            pass
        elif url.path.startswith("/temperature/"):
            sensor_id = unquote(
                url.path[len("/temperature/"):]
            ).strip()

            if not sensor_id or "/" in sensor_id:
                self.send_json(400, {"error": "Invalid sensor ID"})
                return
        else:
            self.send_json(404, {"error": "Not Found"})
            return

        if not location:
            location = LOCATIONS.get(sensor_id, "Unknown")

        if not sensor_id:
            sensor_id = SENSOR_IDS.get(location, "0")

        timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )

        self.send_json(
            200,
            {
                "value": generate_temperature(sensor_id),
                "unit": "°C",
                "timestamp": timestamp,
                "location": location,
                "status": "active",
                "sensor_id": sensor_id,
                "sensor_type": "temperature",
                "description": f"Temperature sensor in {location}",
            },
        )

    def send_json(self, status_code, data):
        body = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        TemperatureHandler,
    )

    print(
        f"Temperature API listening on port {PORT}",
        flush=True,
    )

    server.serve_forever()