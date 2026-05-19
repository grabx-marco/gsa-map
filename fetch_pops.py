#!/usr/bin/env python3
"""
Fetches Microsoft Global Secure Access Points of Presence,
geocodes them via Nominatim, and generates a standalone Leaflet.js map.

Usage:
    python3 fetch_pops.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

MICROSOFT_URL = (
    "https://learn.microsoft.com/en-us/entra/global-secure-access/"
    "reference-points-of-presence"
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OUTPUT_FILE = Path("map.html")

# Nominatim requires a descriptive User-Agent per usage policy:
# https://operations.osmfoundation.org/policies/nominatim/
HEADERS = {"User-Agent": "gsa-map/1.0 (https://github.com/your-org/gsa-map)"}

REGION_KEYWORDS = {
    "Asia Pacific": "APAC",
    "APAC": "APAC",
    "Europe Middle East": "EMEA",
    "EMEA": "EMEA",
    "Latin America": "LATAM",
    "LATAM": "LATAM",
    "North America": "NA",
}


def fetch_pops() -> list[dict]:
    """Fetch and parse GSA PoP locations from Microsoft documentation."""
    print("Fetching PoP data from Microsoft Learn...")
    resp = requests.get(MICROSOFT_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # Microsoft Learn returns UTF-8 but misreports encoding

    soup = BeautifulSoup(resp.text, "html.parser")
    pops = []
    current_region = None

    for element in soup.find_all(["h2", "h3", "table"]):
        if element.name in ("h2", "h3"):
            for keyword, region in REGION_KEYWORDS.items():
                if keyword in element.get_text():
                    current_region = region
                    break

        elif element.name == "table" and current_region:
            headers = [th.get_text(strip=True) for th in element.find_all("th")]
            col = {}
            for i, h in enumerate(headers):
                if "Physical Location" in h:
                    col["location"] = i
                elif "Global Secure Access service" in h:
                    col["gsa"] = i
                elif "Remote network" in h or "Remote Network" in h:
                    col["remote"] = i
                elif "Azure Region" in h:
                    col["azure"] = i

            if "location" not in col or "gsa" not in col:
                continue

            for row in element.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) <= max(col["location"], col["gsa"]):
                    continue
                if "✅" not in cells[col["gsa"]].get_text():
                    continue

                location = cells[col["location"]].get_text(strip=True)
                parts = [p.strip() for p in location.split(",")]

                pops.append({
                    "azure_region": cells[col["azure"]].get_text(strip=True) if "azure" in col else "",
                    "location": location,
                    "city": parts[0],
                    "country": parts[-1],
                    "region": current_region,
                    "remote_network": "remote" in col and "✅" in cells[col["remote"]].get_text(),
                    "lat": None,
                    "lon": None,
                })

    print(f"Found {len(pops)} locations with Global Secure Access service deployed.")
    return pops


def geocode(location: str, city: str, country: str) -> tuple[float, float] | None:
    """Geocode a location string via Nominatim, with fallback queries."""
    for query in [location, f"{city}, {country}", city]:
        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 1},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception as exc:
            print(f"  Error geocoding '{query}': {exc}")
        time.sleep(1)
    return None


def build_map(pops: list[dict]) -> str:
    """Generate a self-contained Leaflet.js HTML map with embedded location data."""
    geocoded = [p for p in pops if p["lat"] is not None]
    remote_count = sum(1 for p in geocoded if p["remote_network"])
    markers_json = json.dumps(geocoded, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Secure Access – Points of Presence</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; }}
        #map {{ width: 100vw; height: 100vh; }}
        #legend {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            border-radius: 8px;
            padding: 12px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            font-size: 13px;
            min-width: 210px;
        }}
        #legend h3 {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #323130;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 5px 0;
            color: #323130;
        }}
        .dot {{
            width: 13px;
            height: 13px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 0 1.5px #555;
            flex-shrink: 0;
        }}
        .stats {{
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid #edebe9;
            color: #605e5c;
            font-size: 12px;
            line-height: 1.6;
        }}
        #source {{
            position: absolute;
            bottom: 6px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            font-size: 11px;
            color: #605e5c;
            background: rgba(255,255,255,0.85);
            padding: 2px 10px;
            border-radius: 4px;
            white-space: nowrap;
        }}
        #source a {{ color: #0078d4; text-decoration: none; }}
        #source a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div id="map"></div>

    <div id="legend">
        <h3>Global Secure Access PoPs</h3>
        <div class="legend-item">
            <div class="dot" style="background:#0078d4"></div>
            GSA service deployed
        </div>
        <div class="legend-item">
            <div class="dot" style="background:#107c10"></div>
            GSA + Remote Network Gateway
        </div>
        <div class="stats">
            {len(geocoded)} of {len(pops)} locations shown<br>
            {remote_count} with Remote Network Gateway
        </div>
    </div>

    <div id="source">
        Data: <a href="{MICROSOFT_URL}" target="_blank">Microsoft Learn</a>
        &nbsp;·&nbsp; Map: &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        const map = L.map('map').setView([30, 10], 2);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }}).addTo(map);

        const pops = {markers_json};

        pops.forEach(p => {{
            const color = p.remote_network ? '#107c10' : '#0078d4';
            const remoteLabel = p.remote_network
                ? '<span style="color:#107c10">&#10003; Active</span>'
                : '<span style="color:#a19f9d">&#8212;</span>';

            const popup = `
                <b style="font-size:14px">${{p.location}}</b><br>
                <table style="margin-top:6px;font-size:12px;border-collapse:collapse">
                    <tr><td style="color:#605e5c;padding-right:8px">Azure Region</td><td>${{p.azure_region}}</td></tr>
                    <tr><td style="color:#605e5c;padding-right:8px">GSA Region</td><td>${{p.region}}</td></tr>
                    <tr><td style="color:#605e5c;padding-right:8px">Remote Network</td><td>${{remoteLabel}}</td></tr>
                </table>`;

            L.circleMarker([p.lat, p.lon], {{
                radius: 8,
                fillColor: color,
                color: '#ffffff',
                weight: 2,
                fillOpacity: 0.9,
            }}).bindPopup(popup).addTo(map);
        }});
    </script>
</body>
</html>"""


def main() -> None:
    pops = fetch_pops()

    print(f"Geocoding {len(pops)} locations via Nominatim (1 request/sec)...")
    for i, pop in enumerate(pops):
        print(f"  [{i + 1:2d}/{len(pops)}] {pop['location']}")
        coords = geocode(pop["location"], pop["city"], pop["country"])
        if coords:
            pop["lat"], pop["lon"] = coords
        else:
            print(f"  WARNING: Could not geocode '{pop['location']}'")
        time.sleep(1)

    OUTPUT_FILE.write_text(build_map(pops), encoding="utf-8")
    print(f"\nMap written to {OUTPUT_FILE} — open it in your browser.")


if __name__ == "__main__":
    main()
