from tinydb import TinyDB, Query
from mechanism import Mechanism, Gelenk, Stab

db = TinyDB("mechanism_db.json")
mechanisms_table = db.table("mechanisms")

def save_mechanism_to_db(name, gelenke, staebe, radius):
    mechanism_data = {
        "name": name,
        "gelenke": {
            i: {
                "x": g.x,
                "y": g.y,
                "is_static": g.is_static,
                "is_rotating": g.is_rotating,
                "is_tracked": g.is_tracked
            } for i, g in enumerate(gelenke)
        },
        "staebe": {
            i: {
                "gelenk1": gelenke.index(s.gelenk1),
                "gelenk2": gelenke.index(s.gelenk2)
            } for i, s in enumerate(staebe)
        },
        "radius": radius
    }
    mechanisms_table.insert(mechanism_data)

def load_mechanism_from_db(name):
    Mechanism = Query()
    result = mechanisms_table.get(Mechanism.name == name)
    if result is None:
        return None

    try:
        gelenke = [Gelenk(g["x"], g["y"], g["is_static"], g["is_rotating"], g["is_tracked"]) for g in result["gelenke"].values()]
        staebe = [Stab(gelenke[s["gelenk1"]], gelenke[s["gelenk2"]]) for s in result["staebe"].values()]
        radius = result["radius"]
        return Mechanism(gelenke, staebe, radius)
    except KeyError as e:
        print(f"KeyError: {e}")
        return None
    except IndexError as e:
        print(f"IndexError: {e}")
        return None
