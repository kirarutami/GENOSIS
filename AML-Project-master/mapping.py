import csv
import re # Modul untuk regular expression, buat bersihin IRI

def clean_iri(iri_string):
    """Membersihkan IRI dari embel-embel tipe data (^^<...>)"""
    return re.sub(r'\^\^<.*>$', '', iri_string)

def create_aml_reference_alignment(csv_filepath, output_xml_filepath, local_onto_iri, global_onto_iri):
    """
    Membuat file reference alignment dalam format RDF/XML untuk AML
    dari file CSV input (hasil SPARQL).
    """
    mappings_xml = []
    try:
        # Modifikasi di sini: tambahkan delimiter=';'
        with open(csv_filepath, mode='r', encoding='utf-8') as csvfile:
            # Beritahu DictReader kalau pemisahnya adalah titik koma
            reader = csv.DictReader(csvfile, delimiter=';') 
            
            # Cek header lagi setelah menentukan delimiter
            expected_headers = ['genosisEntityIRI', 'localOFBEntityIRI']
            if not reader.fieldnames or not all(col in reader.fieldnames for col in expected_headers):
                print(f"Error: File CSV '{csv_filepath}' harus memiliki header 'genosisEntityIRI' dan 'localOFBEntityIRI' yang dipisahkan oleh ';'.")
                print(f"Header yang ditemukan setelah delimiter ';': {reader.fieldnames}")
                # Coba tampilkan baris pertama untuk debug jika header masih salah
                try:
                    csvfile.seek(0) # Kembali ke awal file
                    first_line = csvfile.readline()
                    print(f"Baris pertama file CSV: {first_line.strip()}")
                    # Cek apakah header yang diharapkan ada di baris pertama
                    if all(expected_header in first_line for expected_header in expected_headers):
                        print("INFO: Header terdeteksi di baris pertama, tapi mungkin masalah delimiter saat parsing DictReader.")
                        # Jika DictReader masih gagal, mungkin perlu parsing manual baris header
                        # Untuk sekarang, kita lanjutkan dengan asumsi DictReader akan bekerja dengan delimiter yang benar
                    else:
                        print("ERROR: Header yang diharapkan ('genosisEntityIRI', 'localOFBEntityIRI') tidak ditemukan sebagai kolom terpisah di baris pertama.")
                        print("Pastikan pemisah kolom di file CSV Anda adalah titik koma (;) dan header sudah benar.")
                        return
                except Exception as e_debug:
                    print(f"Error saat debug baris pertama: {e_debug}")
                    return


            for row in reader:
                # Ambil nilai dan bersihkan dari ^^<...>
                entity_local_raw = row.get('localOFBEntityIRI')
                entity_global_raw = row.get('genosisEntityIRI')

                if entity_local_raw is None or entity_global_raw is None:
                    print(f"Warning: Baris terlewat karena kolom tidak lengkap: {row}")
                    continue
                
                entity_local = clean_iri(entity_local_raw)
                entity_global = clean_iri(entity_global_raw)
                
                cell_xml = f"""
    <map>
      <Cell>
        <entity1 rdf:resource="{entity_local}"/>
        <entity2 rdf:resource="{entity_global}"/>
        <measure rdf:datatype="http://www.w3.org/2001/XMLSchema#float">1.0</measure>
        <relation>=</relation>
      </Cell>
    </map>"""
                mappings_xml.append(cell_xml)
    
    except FileNotFoundError:
        print(f"Error: File CSV '{csv_filepath}' tidak ditemukan.")
        return
    except Exception as e:
        print(f"Error saat memproses file CSV: {e}")
        return

    if not mappings_xml:
        print("Tidak ada mapping yang valid ditemukan/diproses dari file CSV.")
        return

    alignment_template = f"""<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns="http://knowledgeweb.semanticweb.org/heterogeneity/alignment"
         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:xsd="http://www.w3.org/2001/XMLSchema#">
<Alignment>
  <xml>yes</xml>
  <level>0</level>
  <type>11</type>
  <onto1><Ontology rdf:about="{local_onto_iri}"/></onto1>
  <onto2><Ontology rdf:about="{global_onto_iri}"/></onto2>
  {''.join(mappings_xml)}
</Alignment>
</rdf:RDF>
"""

    try:
        with open(output_xml_filepath, mode='w', encoding='utf-8') as outfile:
            outfile.write(alignment_template)
        print(f"File reference alignment berhasil dibuat: '{output_xml_filepath}'")
    except Exception as e:
        print(f"Error saat menulis file XML: {e}")

# --- CARA PENGGUNAAN SCRIPT ---
if __name__ == "__main__":
    input_csv_file = r"D:\thesis\AML-Project-master\OFB mappings_for_aml.csv" 
    output_reference_file = "reference_alignment_OFB_genosis.rdf" 
    
    # Pastikan IRI ini benar
    local_OFB_ontology_iri = "http://saralutami.org/MicrobloggingPlatforms" 
    genosis_ontology_iri = "http://example.org/genosis.owl"

    create_aml_reference_alignment(input_csv_file, output_reference_file, local_OFB_ontology_iri, genosis_ontology_iri)