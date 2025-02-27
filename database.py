from tinydb import TinyDB, Query
from mechanism import Mechanism, Gelenk, Stab

db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

def save_mechanism_to_db(name, gelenke, staebe, radius):
    mechanisms_table.insert({
        "name": name,
        "gelenke": [
            {
                "x": g.x, 
                "y": g.y, 
                "is_static": g.is_static, 
                "is_rotating": g.is_rotating, 
                "is_tracked": g.is_tracked
            } for g in gelenke],
        "staebe": [{"gelenk1": gelenke.index(s.gelenk1), "gelenk2": gelenke.index(s.gelenk2)} for s in staebe],
        "radius": radius
    })

def load_mechanism_from_db(name):
    MechanismQuery = Query()
    result = mechanisms_table.get(MechanismQuery.name == name)
    if result:
        gelenke = [
            Gelenk(
                g["x"],
                g["y"],
                g.get("is_static", g.get("static", False)),
                g.get("is_rotating", g.get("rotating", False)),
                g.get("is_tracked", g.get("tracked", False))
            ) for g in result["gelenke"]
        ]
        # Verwende s[0] und s[1] statt s["gelenk1"] etc.
        staebe = [Stab(gelenke[s[0]], gelenke[s[1]]) for s in result["staebe"]]
        radius = result["radius"]
        return Mechanism(gelenke, staebe, radius)
    return None
