import requests,json
H={"User-Agent":"kittur-research/0.1"}
names=["Kittur","Kittur Fort","Sangolli","Nandagad","Bailhongal","Belgaum Fort","Dharwad","Khanapur, Belgaum","Hubli","Deshnur","Belgaum","Sampgaon","Rajhansgad","Kittur Rani Chennamma","Sangolli Rayanna"]
for n in names:
    r=requests.get("https://www.wikidata.org/w/api.php",params=dict(action="wbsearchentities",search=n,language="en",format="json",limit=4),headers=H).json()
    for s in r.get("search",[]):
        e=requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{s['id']}.json",headers=H).json()["entities"][s["id"]]
        c=e["claims"].get("P625")
        if c:
            v=c[0]["mainsnak"]["datavalue"]["value"]; print(n,"|",s["id"],s.get("label"),"|",s.get("description",""),"|",round(v["latitude"],5),round(v["longitude"],5))
