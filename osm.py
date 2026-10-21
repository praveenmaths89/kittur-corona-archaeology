import requests, geopandas as gpd, json
from shapely.geometry import Point, LineString, Polygon
q="""[out:json][timeout:180];(
nwr["historic"](15.45,74.45,15.90,74.95);
nwr["natural"="water"](15.45,74.45,15.90,74.95);
nwr["water"](15.45,74.45,15.90,74.95);
nwr["landuse"="reservoir"](15.45,74.45,15.90,74.95);
nwr["amenity"="place_of_worship"](15.45,74.45,15.90,74.95);
node["place"~"city|town|village|hamlet"](15.45,74.45,15.90,74.95);
way["waterway"~"river|stream|canal"](15.45,74.45,15.90,74.95);
way["highway"~"motorway|trunk|primary|secondary|tertiary"](15.45,74.45,15.90,74.95);
);out geom tags;"""
r=requests.post("https://overpass.kumi.systems/api/interpreter",data={"data":q},headers={"User-Agent":"kittur-research"},timeout=300); r.raise_for_status()
E=r.json()["elements"]; print(len(E))
rows=[]
for e in E:
    t=e.get("tags",{})
    if e["type"]=="node": g=Point(e["lon"],e["lat"])
    elif e["type"]=="way" and "geometry" in e:
        c=[(p["lon"],p["lat"]) for p in e["geometry"]]
        g=Polygon(c) if c[0]==c[-1] and len(c)>3 and "highway" not in t and "waterway" not in t else LineString(c)
    elif e["type"]=="relation" and "bounds" in e:
        b=e["bounds"]; g=Point((b["minlon"]+b["maxlon"])/2,(b["minlat"]+b["maxlat"])/2)
    else: continue
    if "historic" in t: cat="historic"
    elif "waterway" in t: cat="waterway"
    elif "highway" in t: cat="road"
    elif "place" in t: cat="place"
    elif t.get("amenity")=="place_of_worship": cat="worship"
    else: cat="water"
    rows.append(dict(osm_id=f'{e["type"]}/{e["id"]}',category=cat,name=t.get("name",""),name_kn=t.get("name:kn",""),tags=json.dumps(t,ensure_ascii=False),geometry=g))
g=gpd.GeoDataFrame(rows,crs=4326); g.to_file("osm_raw.gpkg")
print(g.category.value_counts()); print(g[g.category=="historic"][["name","tags"]].to_string()[:4000])
