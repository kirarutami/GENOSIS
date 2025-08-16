import rdflib
import csv

# Load RDF file
rdf_file = 'completev3.rdf'  # Ganti dengan path ke file RDF Anda
g = rdflib.Graph()
g.parse(rdf_file)

# SPARQL query for Object Properties
sparql_query_object_properties = """
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

# SPARQL query for Data Properties
sparql_query_data_properties = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?class ?dataProperty ?classComment ?dataPropertyComment
WHERE {
  ?dataProperty a owl:DatatypeProperty .
  ?dataProperty rdfs:domain ?class .
  
  OPTIONAL { ?class rdfs:comment ?classComment . }
  OPTIONAL { ?dataProperty rdfs:comment ?dataPropertyComment . }
}
"""

# SPARQL query for Classes and Sub-classes
sparql_query_classes_subclasses = """
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

# Function to write query results to CSV
def write_query_to_csv(query, output_file, header):
    qres = g.query(query)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in qres:
            writer.writerow([str(row[var] if row[var] else '') for var in header])

# Output CSV files
write_query_to_csv(
    sparql_query_object_properties, 
    'output_object_properties.csv', 
    ['subject', 'predicate', 'object', 'subjectComment', 'predicateComment', 'objectComment']
)

write_query_to_csv(
    sparql_query_data_properties, 
    'output_data_properties.csv', 
    ['class', 'dataProperty', 'classComment', 'dataPropertyComment']
)

write_query_to_csv(
    sparql_query_classes_subclasses, 
    'output_classes_subclasses.csv', 
    ['class', 'subClass', 'classComment', 'subClassComment']
)

print("Data extraction completed. Results written to respective CSV files.")
