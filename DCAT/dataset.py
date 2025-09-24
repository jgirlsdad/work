from rdflib import Graph, Namespace
from rdflib.namespace import SKOS
import pandas as pd

# Correct RDF URL for EU Languages
LANGUAGE_RDF_URL = "https://publications.europa.eu/resource/authority/language"

# Load RDF
print("Loading language vocabulary...")
g = Graph()
g.parse(LANGUAGE_RDF_URL,format="xml")

# Extract English labels and URIs
entries = []
for s, p, o in g.triples((None, SKOS.prefLabel, None)):
    print(s,p,o)
    if o.language == "english":
        entries.append({"label": str(o), "uri": str(s)})

# Create DataFrame
df = pd.DataFrame(entries)

# Lookup function
def lookup_language(term):
    matches = df[df["label"].str.contains(term, case=False)]
    if not matches.empty:
        print(matches.to_string(index=False))
    else:
        print(f"No match for '{term}'")

# Try searching
print("\n🔎 Search example for 'french':")
lookup_language("eng")

# Optional: Save to CSV
df.to_csv("language_vocab.csv", index=False)
