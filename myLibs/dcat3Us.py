"""
dcat_us_3_model.py

Loads and parses the DCAT-US 3.0 SHACL shapes file directly from GitHub
and returns a structured dictionary describing:

- Each metadata class (Catalog, Dataset, Distribution, etc.)
- Class-level requirements (mandatory / optional / recommended)
- Property-level constraints (mandatory / optional)
- Definitions, labels, cardinalities

This function runs fast and can be called on demand.

## Add library path
import sys
sys.path.insert(0, '/home/joe/work/myLibs')

## Example usage:
model, modelH = load_dcat_us_3_model()
with open("dcat_us_3_model.json", "w", encoding="utf-8") as f:
    json.dump(model, f, indent=2, ensure_ascii=False)
 
"""

from rdflib import Graph, RDF, RDFS, SH
import json

# ============================================================
# URLs & Namespaces
# ============================================================

DCAT_US_3_SHACL_URL = (
    "https://raw.githubusercontent.com/DOI-DO/dcat-us/main/shacl/dcat-us_3.0_shacl_shapes.ttl"
)

VALID_CLASS_PREFIXES = [
    "http://www.w3.org/ns/dcat#",
    "http://purl.org/dc/terms/",
    "http://xmlns.com/foaf/0.1/",
    "http://www.w3.org/ns/locn#",
    "http://www.w3.org/2006/vcard/ns#",
]

# ============================================================
# Class-level requirement rules (from DCAT-US documentation)
# ============================================================

CLASS_USAGE = {
    "http://www.w3.org/ns/dcat#Catalog": {
        "requirement": "mandatory",
        "min_instances": 1,
        "max_instances": 1,
    },
    "http://www.w3.org/ns/dcat#Dataset": {
        "requirement": "mandatory",
        "min_instances": 1,
        "max_instances": None,
    },
    "http://www.w3.org/ns/dcat#Distribution": {
        "requirement": "recommended_if_applicable",
        "min_instances": 0,
        "max_instances": None,
    },
    "http://xmlns.com/foaf/0.1/Agent": {
        "requirement": "mandatory_if_applicable",
        "min_instances": 0,
        "max_instances": None,
    },
    "http://www.w3.org/2006/vcard/ns#Kind": {
        "requirement": "mandatory_if_applicable",
        "min_instances": 0,
        "max_instances": None,
    },
    "http://purl.org/dc/terms/PeriodOfTime": {
        "requirement": "optional",
        "min_instances": 0,
        "max_instances": None,
    },
    "http://www.w3.org/ns/locn#Geometry": {
        "requirement": "optional",
        "min_instances": 0,
        "max_instances": None,
    },
}

# ============================================================
# Callable function
# ============================================================

def load_dcat_us_3_model():
    """
    Fetches and parses the DCAT-US 3.0 SHACL file and returns a structured
    dictionary describing classes, mandatory/recommended/optional properties,
    definitions, labels, and cardinalities.

    Returns:
        dict: nested structure keyed by class URI.

    Example:
        model = load_dcat_us_3_model()
        model["http://www.w3.org/ns/dcat#Dataset"]["mandatory"]
    """

    g = Graph()
    g.parse(DCAT_US_3_SHACL_URL, format="turtle")

    model = {}

    # Iterate through SHACL NodeShapes
    for shape in g.subjects(RDF.type, SH.NodeShape):

        targets = list(g.objects(shape, SH.targetClass))
        if not targets:
            continue

        target = str(targets[0])

        # Skip helper shapes
        if not any(target.startswith(prefix) for prefix in VALID_CLASS_PREFIXES):
            continue

        # Build class structure entry
        class_entry = {
            "shape": str(shape),
            "class_usage": CLASS_USAGE.get(
                target,
                {
                    "requirement": "optional",
                    "min_instances": 0,
                    "max_instances": None,
                },
            ),
            "mandatory": {},
            "recommended": {},
            "optional": {},
        }

        # Extract property shapes
        for pshape in g.objects(shape, SH.property):
            prop = g.value(pshape, SH.path)
            if prop is None:
                continue
            prop = str(prop)

            mincount = g.value(pshape, SH.minCount)
            maxcount = g.value(pshape, SH.maxCount)
            definition = g.value(pshape, SH.description) or g.value(pshape, RDFS.comment)
            label = g.value(pshape, RDFS.label)

            entry = {}
            if definition:
                entry["definition"] = str(definition)
            if label:
                entry["label"] = str(label)
            if mincount:
                entry["minCount"] = int(mincount)
            if maxcount:
                entry["maxCount"] = int(maxcount)

            # Mandatory vs optional split
            if mincount and int(mincount) >= 1:
                class_entry["mandatory"][prop] = entry
            else:
                class_entry["optional"][prop] = entry

        model[target] = class_entry

    modelH={}
    for k,d in model.items():
        r=d['class_usage']['requirement']
        if r not in modelH:
            modelH[r]={}
        modelH[r][k]=d
        for k2,d2 in d['class_usage'].items():
    #       if d2['requirement'] == 'mandatory':
            if k2 == "requirement" and d2 == "mandatory":
                print('     ',k2,"-", d2,type(d2))

    return model,modelH

