from rdflib import Graph

# Load RDF
g = Graph()
g.parse(r"D:\thesis\Global Ontology\example.owl", format="xml")  # gunakan r-string agar backslash aman

# SPARQL Query
query = """
PREFIX : <http://example.org/gsmfo.owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?post ?timestamp
WHERE {
  ?post rdf:type ?type .
  ?type rdfs:subClassOf* :Global_Post .
  ?post :Global_hasPostTimestamp ?timestamp .
}
"""

# Eksekusi
for row in g.query(query):
    print(f"Post: {row.post}, Timestamp: {row.timestamp}")
