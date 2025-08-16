import rdflib
import csv

# Load RDF file
rdf_file = 'mf-user.rdf'  # Ganti dengan path ke file RDF Anda
g = rdflib.Graph()
g.parse(rdf_file)

# SPARQL query
sparql_query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?class ?subClass ?classComment ?subClassComment
WHERE {
  ?subClass rdfs:subClassOf ?class .
  ?class a owl:Class .
  
  OPTIONAL { ?class rdfs:comment ?classComment . }
  OPTIONAL { ?subClass rdfs:comment ?subClassComment . }
}
"""

# Execute SPARQL query
qres = g.query(sparql_query)

# Define output CSV file
csv_file = 'output_classes_subclasses.csv'

# Write results to CSV
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Write header
    writer.writerow(['Class', 'SubClass', 'ClassComment', 'SubClassComment'])
    # Write rows
    for row in qres:
        writer.writerow([
            str(row['class']), 
            str(row['subClass']), 
            str(row['classComment'] if row['classComment'] else ''), 
            str(row['subClassComment'] if row['subClassComment'] else '')
        ])

print(f"Data has been written to {csv_file}")
