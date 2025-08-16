import rdflib
import csv

# Load RDF file
rdf_file = 'D:\Dokumentasi\Tesis\V3-OSN\completev3.rdf'  # Ganti dengan path ke file RDF Anda
g = rdflib.Graph()
g.parse(rdf_file)

# SPARQL query
sparql_query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?subject ?predicate ?object ?subjectComment ?predicateComment ?objectComment
WHERE {
  ?predicate a owl:ObjectProperty .
  ?predicate rdfs:domain ?subject .
  ?predicate rdfs:range ?object .
  
  OPTIONAL { ?subject rdfs:comment ?subjectComment . }
  OPTIONAL { ?predicate rdfs:comment ?predicateComment . }
  OPTIONAL { ?object rdfs:comment ?objectComment . }
  
  FILTER NOT EXISTS { ?subClass rdfs:subClassOf ?subject . ?subClass ?predicate ?object . }
}
"""

# Execute SPARQL query
qres = g.query(sparql_query)

# Define output CSV file
csv_file = 'output_object_properties.csv'

# Write results to CSV
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Write header
    writer.writerow(['Subject', 'Predicate', 'Object', 'SubjectComment', 'PredicateComment', 'ObjectComment'])
    # Write rows
    for row in qres:
        writer.writerow([str(row.subject), str(row.predicate), str(row.object), 
                         str(row.subjectComment if row.subjectComment else ''), 
                         str(row.predicateComment if row.predicateComment else ''), 
                         str(row.objectComment if row.objectComment else '')])

print(f"Data has been written to {csv_file}")
