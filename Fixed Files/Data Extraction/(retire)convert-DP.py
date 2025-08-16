import rdflib
import csv

# Load RDF file
rdf_file = 'Local OSN.rdf'  # Ganti dengan path ke file RDF Anda
g = rdflib.Graph()
g.parse(rdf_file)

# SPARQL query
sparql_query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?class ?dataProperty ?classComment ?dataPropertyComment
WHERE {
  ?dataProperty a owl:DatatypeProperty .
  ?dataProperty rdfs:domain ?class .
  
  # Mengambil komentar untuk kelas (jika ada)
  OPTIONAL { ?class rdfs:comment ?classComment . }
  
  # Mengambil komentar untuk Data Property (jika ada)
  OPTIONAL { ?dataProperty rdfs:comment ?dataPropertyComment . }
}
"""

# Execute SPARQL query
qres = g.query(sparql_query)

# Define output CSV file
csv_file = 'DP OSN.csv'

# Write results to CSV
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Write header
    writer.writerow(['Class', 'DataProperty', 'ClassComment', 'DataPropertyComment'])
    # Write rows
    for row in qres:
        writer.writerow([
            str(row['class']), 
            str(row['dataProperty']), 
            str(row['classComment'] if row['classComment'] else ''), 
            str(row['dataPropertyComment'] if row['dataPropertyComment'] else '')
        ])

print(f"Data has been written to {csv_file}")
