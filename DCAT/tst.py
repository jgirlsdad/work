import csv
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, XSD

# Define Namespaces
EX = Namespace("http://example.org/dataset/")
DATA_THEME = Namespace("http://publications.europa.eu/resource/authority/data-theme/")

# Load your CSV
input_file = "datasets_metadata.csv"
g = Graph()
g.bind("dcat", DCAT)
g.bind("dct", DCTERMS)
g.bind("foaf", FOAF)

with open(input_file, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        dataset_uri = EX[row['id']]
        g.add((dataset_uri, RDF.type, DCAT.Dataset))
        g.add((dataset_uri, DCTERMS.title, Literal(row['title'])))
        g.add((dataset_uri, DCTERMS.description, Literal(row['description'])))
        g.add((dataset_uri, DCTERMS.issued, Literal(row['issued'], datatype=XSD.date)))
        g.add((dataset_uri, DCTERMS.modified, Literal(row['modified'], datatype=XSD.date)))
        g.add((dataset_uri, DCTERMS.publisher, Literal(row['publisher'])))
        g.add((dataset_uri, DCTERMS.license, URIRef(row['license'])))
        g.add((dataset_uri, DCAT.theme, URIRef(DATA_THEME[row['theme']])))
        
        for keyword in row['keywords'].split(','):
            g.add((dataset_uri, DCAT.keyword, Literal(keyword.strip())))

        # Add a distribution
        dist_uri = URIRef(f"{dataset_uri}/distribution")
        g.add((dataset_uri, DCAT.distribution, dist_uri))
        g.add((dist_uri, RDF.type, DCAT.Distribution))
        g.add((dist_uri, DCAT.downloadURL, URIRef(row['download_url'])))

# Serialize the graph
g.serialize("dcat3_output.ttl", format="turtle")
