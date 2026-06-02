import os
import json

def clean_mongo_types(obj):
    if isinstance(obj, dict):
        if len(obj) == 1 and "$oid" in obj:
            return obj["$oid"]
        if len(obj) == 1 and "$date" in obj:
            return obj["$date"]
        return {k: clean_mongo_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_mongo_types(i) for i in obj]
    return obj

def main():
    d = "vihil collection"
    kb = {}
    for f in os.listdir(d):
        if not f.endswith(".json"): continue
        col_name = f.replace("Vihil_Web.", "").replace(".json", "")
        filepath = os.path.join(d, f)
        with open(filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            cleaned = clean_mongo_types(data)
            kb[col_name] = cleaned

    # Reconstruct company object for qa_engine compatibility
    company = {"contact": {}}
    if "contactdetails" in kb:
        cd = kb["contactdetails"]
        if isinstance(cd, list) and cd:
            company["contact"]["contactdetails"] = cd[0]
            
    if "impactmetrixes" in kb:
        im = kb["impactmetrixes"]
        if isinstance(im, list) and im:
            company["stats"] = []
            for k, v in im[0].items():
                if k not in ["_id", "createdAt", "updatedAt", "__v"]:
                    company["stats"].append({"label": k, "value": str(v)})
                    
    kb["company"] = company
    
    # Map the root keys so qa_engine.py can find them naturally
    kb["services"] = kb.get("vihilservices", [])
    kb["what_we_do"] = kb.get("vihilcapabilities", [])
    kb["team"] = kb.get("teammembers", [])

    with open("knowledge_base.json", "w", encoding="utf-8") as out:
        json.dump(kb, out, indent=2, ensure_ascii=False)
    print("Successfully built knowledge_base.json from vihil collection!")

if __name__ == "__main__":
    main()
