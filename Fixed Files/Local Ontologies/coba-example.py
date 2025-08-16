from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD

# Load RDF dari file lokal Anda
g = Graph()
try:
    # Gunakan r-string (r"...") untuk memastikan path file di Windows terbaca dengan benar
    g.parse(r"D:\thesis\Fixed Files\Local Ontologies\Local OSN.rdf", format="xml")
    print("Graph berhasil di-load.")
    print(f"Total triples dalam graph: {len(g)}")
except FileNotFoundError:
    print("Error: File .rdf tidak ditemukan. Pastikan path file sudah benar.")
    exit()

# SPARQL Query dengan tambahan FILTER untuk "Facebook"
query = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX ex: <http://www.w3.org/2002/07/owl#>

SELECT ?timestamp ?interactionType ?user ?content ?location ?device ?ip
WHERE {
  {
    BIND("Post" AS ?interactionType)
    ?interaction_uri rdf:type ex:Posts ;
                   ex:belongsToPlatform ?platform ;     
                   ex:hasPostContent ?content ;
                   ex:hasPostTimestamp ?timestamp .
    BIND(?interaction_uri AS ?user)

    OPTIONAL { ?interaction_uri ex:hasMessageLocation ?location . }
    OPTIONAL { ?interaction_uri ex:hasDeviceInfo ?device . }
    OPTIONAL { ?interaction_uri ex:hasUserInteractionIP ?ip . }
  }
  UNION
  {
    BIND("Comment" AS ?interactionType)
    ?interaction_uri rdf:type ex:TextComment ;
                   ex:belongsToPlatform ?platform ;     
                   ex:hasCommentText ?content ;
                   ex:hasCommentTimestamp ?timestamp .
    BIND(?interaction_uri AS ?user)

    OPTIONAL { ?interaction_uri ex:hasMessageLocation ?location . }
    OPTIONAL { ?interaction_uri ex:hasDeviceInfo ?device . }
    OPTIONAL { ?interaction_uri ex:hasUserInteractionIP ?ip . }
  }
  UNION
  {
    BIND("Direct Message" AS ?interactionType)
    ?interaction_uri rdf:type ex:TextMessage ;
                   ex:belongsToPlatform ?platform ;     
                   ex:sendsTextMessage ?user ;
                   ex:hasMessageText ?content ;
                   ex:hasMessageSendTimestamp ?timestamp .

    OPTIONAL { ?interaction_uri ex:hasMessageLocation ?location . }
    OPTIONAL { ?interaction_uri ex:hasDeviceInfo ?device . }
    OPTIONAL { ?interaction_uri ex:hasUserInteractionIP ?ip . }
  }

  # Filter hasil untuk hanya menampilkan data dari Facebook
  FILTER(STR(?platform) = "Facebook") # <-- BARIS FILTER UTAMA DITAMBAHKAN
}
ORDER BY ?timestamp
"""

print("\nMengeksekusi SPARQL query untuk linimasa peristiwa (FILTER: Facebook)...")
print("-" * 60)

# Eksekusi query dan cetak hasilnya
results = g.query(query)

if not results:
    print("Query tidak menemukan hasil untuk platform Facebook.")
else:
    for i, row in enumerate(results):
        # Mengakses hasil berdasarkan nama variabel yang di-SELECT
        print(f"EVENT #{i+1}")
        print(f"  Timestamp       : {row.timestamp}")
        print(f"  Interaction Type: {row.interactionType}")
        print(f"  User/Source     : {row.user}")
        print(f"  Content         : {row.content}")
        
        # Cetak nilai dari OPTIONAL jika ada (tidak None)
        if row.location:
            print(f"  Location        : {row.location}")
        if row.device:
            print(f"  Device Info     : {row.device}")
        if row.ip:
            print(f"  IP Address      : {row.ip}")
        print("-" * 60)