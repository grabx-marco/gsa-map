# GSA Map – Global Secure Access Points of Presence

An interactive map of all Microsoft **Global Secure Access (GSA)** Points of Presence, built with [Leaflet.js](https://leafletjs.com/) and [OpenStreetMap](https://www.openstreetmap.org/).

The script automatically fetches the current PoP list from Microsoft Learn, geocodes each location using [Nominatim](https://nominatim.openstreetmap.org/), and produces a standalone `map.html` that runs entirely in the browser — no server required.

---

## Features

- Fetches live data from the [Microsoft Learn reference page](https://learn.microsoft.com/en-us/entra/global-secure-access/reference-points-of-presence)
- Filters to only locations where **Global Secure Access service is deployed**
- Color-coded markers:
  - **Blue** — GSA service deployed
  - **Green** — GSA service + Remote Network Gateway active
- Popup per marker with Azure Region, GSA region, and Remote Network status
- Fully self-contained output (`map.html` includes all data inline)

---

## Requirements

- Python 3.9 or newer
- Internet access (for fetching Microsoft Learn and Nominatim)

---

## Installation

```bash
git clone https://github.com/thesecurityguy-ch/gsa-map.git
cd gsa-map
pip install -r requirements.txt
```

---

## Usage

```bash
python3 fetch_pops.py
```

The script always fetches fresh data from Microsoft Learn and geocodes all locations. This takes ~45 seconds due to Nominatim's 1 request/sec rate limit.

Then open `map.html` in any browser.

---

## How It Works

```
Microsoft Learn page
        │
        ▼
  fetch_pops.py
        │  BeautifulSoup parses HTML tables
        │  Filters rows where "Global Secure Access service deployed" = ✅
        │
        ▼
  Nominatim API (OpenStreetMap)
        │  Geocodes each "City, Country" string → lat/lon
        │  Rate-limited to 1 request/sec (Nominatim policy)
        │
        ▼
  pops.json  ← cached geocoded data
        │
        ▼
  map.html   ← standalone Leaflet.js map
```

### Files

| File | Description |
|---|---|
| `fetch_pops.py` | Main script: fetch, geocode, generate map |
| `requirements.txt` | Python dependencies |
| `map.html` | Interactive map output (generated, not versioned) |

---

## Data Source

PoP data is sourced from:  
**Microsoft Learn** → [Global Secure Access points of presence and IP addresses](https://learn.microsoft.com/en-us/entra/global-secure-access/reference-points-of-presence)

The script is designed to handle additions automatically:
- **New locations** in existing regional tables are picked up without any code changes
- **New regions** would require adding the heading keyword to `REGION_KEYWORDS` in `fetch_pops.py` (e.g. if Microsoft ever splits EMEA into separate sections)
- **Column renames** on the Microsoft page would require updating the column detection strings in `fetch_pops.py`

---

## Geocoding and Nominatim Policy

This project uses the [Nominatim](https://nominatim.openstreetmap.org/) geocoding API provided by the OpenStreetMap Foundation.

Usage must comply with the [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/):
- Maximum **1 request per second** (enforced by the script)
- A valid **User-Agent** header is sent with every request
If you run this in a CI/CD pipeline or automate refreshes frequently, consider hosting your own Nominatim instance.

---

## Map Tiles

Map tiles are provided by [OpenStreetMap](https://www.openstreetmap.org/) via the standard tile CDN. Usage is subject to the [OpenStreetMap Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/).

For high-traffic or production use, consider a commercial tile provider (e.g., Mapbox, Stadia Maps) or host your own tiles.

---

## License

MIT
