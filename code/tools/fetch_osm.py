"""Download an OpenStreetMap extract (Overpass API) in the schema used by the pipeline.

    python tools/fetch_osm.py <out.gpkg> <south> <west> <north> <east>

The query and the category rules are those used for the Kittur extract (raw/osm/osm_raw.gpkg): historic
features, water bodies and reservoirs, places of worship, settlement nodes, rivers/streams/canals and roads
of class tertiary or above. Output columns: osm_id, category, name, name_kn, tags (JSON), geometry (EPSG:4326).
A sidecar <out>.json records the query, the endpoint and the download time for the provenance table.
"""
import sys, json, datetime
import requests
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def query(s, w, n, e):
    b = f"({s},{w},{n},{e})"
    return f"""[out:json][timeout:180];(
nwr["historic"]{b}; nwr["natural"="water"]{b}; nwr["water"]{b}; nwr["landuse"="reservoir"]{b};
nwr["amenity"="place_of_worship"]{b}; node["place"~"city|town|village|hamlet"]{b};
way["waterway"~"river|stream|canal"]{b}; way["highway"~"motorway|trunk|primary|secondary|tertiary"]{b};
);out geom tags;"""


def category(t):
    if "historic" in t: return "historic"
    if "waterway" in t: return "waterway"
    if "highway" in t: return "road"
    if "place" in t: return "place"
    if t.get("amenity") == "place_of_worship": return "worship"
    return "water"


def main(out, s, w, n, e):
    q = query(s, w, n, e); last = None
    for url in ENDPOINTS:
        try:
            r = requests.post(url, data={"data": q}, headers={"User-Agent": "kittur-research"}, timeout=300)
            r.raise_for_status(); break
        except Exception as ex:          # try the next public endpoint
            last = ex; r = None
    if r is None:
        raise SystemExit(f"Overpass failed: {last}")
    rows = []
    for el in r.json()["elements"]:
        t = el.get("tags", {})
        if el["type"] == "node":
            g = Point(el["lon"], el["lat"])
        elif el["type"] == "way" and "geometry" in el:
            c = [(p["lon"], p["lat"]) for p in el["geometry"]]
            closed = c[0] == c[-1] and len(c) > 3 and "highway" not in t and "waterway" not in t
            g = Polygon(c) if closed else LineString(c)
        elif el["type"] == "relation" and "bounds" in el:
            bb = el["bounds"]; g = Point((bb["minlon"] + bb["maxlon"]) / 2, (bb["minlat"] + bb["maxlat"]) / 2)
        else:
            continue
        rows.append(dict(osm_id=f'{el["type"]}/{el["id"]}', category=category(t), name=t.get("name", ""),
                         name_kn=t.get("name:kn", ""), tags=json.dumps(t, ensure_ascii=False), geometry=g))
    gpd.GeoDataFrame(rows, crs=4326).to_file(out)
    json.dump(dict(endpoint=url, bbox_swne=[s, w, n, e], query=q, n_elements=len(rows),
                   downloaded=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                   licence="ODbL 1.0, (c) OpenStreetMap contributors"), open(str(out) + ".json", "w"), indent=1)
    print(out, len(rows))


if __name__ == "__main__":
    main(sys.argv[1], *map(float, sys.argv[2:6]))
