import csv
import re # Tidak dipakai di versi ini, tapi aman jika ada

def create_new_aml_rdf_from_approved(approved_mappings_csv_path, 
                                     output_rdf_path, 
                                     local_onto_iri, 
                                     global_onto_iri,
                                     relation_symbol="=", 
                                     measure_value=1.0):
    """
    Membuat file RDF reference alignment baru dari daftar mapping yang sudah disetujui.

    Args:
        approved_mappings_csv_path (str): Path ke file CSV berisi mapping yang disetujui.
                                          Format CSV: entity1_local_iri;entity2_genosis_iri
        output_rdf_path (str): Path untuk menyimpan file RDF alignment baru.
        local_onto_iri (str): IRI ontologi lokal (onto1).
        global_onto_iri (str): IRI ontologi global (onto2, GENOSIS).
        relation_symbol (str): Simbol relasi (default '=' untuk ekivalen).
        measure_value (float): Skor kepercayaan (default 1.0 untuk reference).
    """
    map_cell_entries = []
    
    try:
        with open(approved_mappings_csv_path, mode='r', encoding='utf-8') as csvfile:
            # Menggunakan titik koma sebagai delimiter
            reader = csv.DictReader(csvfile, delimiter=';')
            
            # Pastikan header ada
            if not reader.fieldnames or not all(col in reader.fieldnames for col in ['entity1_local_iri', 'entity2_genosis_iri']):
                print("Error: File CSV harus memiliki header 'entity1_local_iri' dan 'entity2_genosis_iri' dipisahkan oleh ';'.")
                print(f"Header yang ditemukan: {reader.fieldnames}")
                return

            for row in reader:
                entity1 = row.get('entity1_local_iri')
                entity2 = row.get('entity2_genosis_iri')

                if not entity1 or not entity2:
                    print(f"Warning: Baris terlewat karena data tidak lengkap: {row}")
                    continue
                
                # Membuat entri <map><Cell>...</Cell></map>
                cell_xml = f"""
    <map>
      <Cell>
        <entity1 rdf:resource="{entity1}"/>
        <entity2 rdf:resource="{entity2}"/>
        <measure rdf:datatype="http://www.w3.org/2001/XMLSchema#float">{measure_value}</measure>
        <relation>{relation_symbol}</relation>
      </Cell>
    </map>"""
                map_cell_entries.append(cell_xml)
                
    except FileNotFoundError:
        print(f"Error: File CSV '{approved_mappings_csv_path}' tidak ditemukan.")
        return
    except Exception as e:
        print(f"Error saat memproses file CSV: {e}")
        return

    if not map_cell_entries:
        print("Tidak ada mapping yang valid untuk ditulis ke file RDF.")
        return

    # Template XML untuk file Alignment
    alignment_rdf_template = f"""<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns="http://knowledgeweb.semanticweb.org/heterogeneity/alignment"
         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:xsd="http://www.w3.org/2001/XMLSchema#">
<Alignment>
  <xml>yes</xml>
  <level>0</level>
  <type>11</type> <onto1><Ontology rdf:about="{local_onto_iri}"/></onto1>
  <onto2><Ontology rdf:about="{global_onto_iri}"/></onto2>
  {''.join(map_cell_entries)}
</Alignment>
</rdf:RDF>
"""

    try:
        with open(output_rdf_path, mode='w', encoding='utf-8') as outfile:
            outfile.write(alignment_rdf_template)
        print(f"File RDF alignment baru berhasil dibuat: '{output_rdf_path}' dengan {len(map_cell_entries)} mapping.")
    except Exception as e:
        print(f"Error saat menulis file XML RDF: {e}")

# --- CARA PENGGUNAAN SCRIPT ---
if __name__ == "__main__":
    # 1. Siapkan file CSV dengan mapping yang sudah Bunda ACC.
    #    Nama kolom HARUS: entity1_local_iri;entity2_genosis_iri
    #    Contoh isi satu baris di CSV (dipisahkan titik koma):
    #    http://saralutami.org/OnlineSocialNetworkSites#User;http://example.org/genosis.owl#OSN:User
    #    http://www.w3.org/2002/07/owl#acceptsEventInvitationFrom;http://example.org/genosis.owl#acceptsEventInvitationFrom
    
    approved_csv_file = "aml_approved_additions.csv" # Ganti dengan nama file CSV Bunda

    # Buat file CSV contoh jika belum ada (HANYA UNTUK DEMO, Bunda buat file ini dari hasil AML yang di-ACC)
    # Bunda bisa copy-paste hasil dari AML yang 100% dan sudah Bunda ACC ke file ini
    # dengan format: IRI_LOKAL;IRI_GENOSIS per baris
    with open(approved_csv_file, mode='w', encoding='utf-8', newline='') as f_demo:
        writer = csv.writer(f_demo, delimiter=';')
        writer.writerow(['entity1_local_iri', 'entity2_genosis_iri']) # Header
        writer.writerow(['http://saralutami.org/OnlineSocialNetworkSites#User', 'http://example.org/genosis.owl#OSN:User'])
        writer.writerow(['http://www.w3.org/2002/07/owl#acceptsEventInvitationFrom', 'http://example.org/genosis.owl#OSN:acceptsEventInvitationFrom']) # Perhatikan namespace OSN: pada genosis entity
        writer.writerow(['http://saralutami.org/OnlineSocialNetworkSites#hasFriend', 'http://example.org/genosis.owl#Global:followsAccount'])


    # 2. Tentukan nama file RDF output yang diinginkan untuk mapping tambahan ini
    output_rdf_additions_file = r"D:\thesis\AML-Project-master\aml_new_potential_additions.csv" 
    
    # 3. IRI ontologi lokal OSN Bunda (sesuaikan jika berbeda)
    local_osn_ontology_iri = "http://saralutami.org/OnlineSocialNetworkSites" 
    
    # 4. IRI ontologi GENOSIS Bunda
    genosis_ontology_iri = "http://example.org/genosis.owl"

    # Jalankan fungsi
    create_new_aml_rdf_from_approved(approved_csv_file, 
                                     output_rdf_additions_file, 
                                     local_osn_ontology_iri, 
                                     genosis_ontology_iri)

    print("\n--- Selesai membuat file RDF untuk mapping tambahan ---")
    print("LANGKAH SELANJUTNYA BUAT BUNDA:")
    print("1. Pastikan file CSV input ('aml_approved_additions.csv' atau nama pilihan Bunda) berisi mapping yang BENAR dan SUDAH BUNDA ACC.")
    print(f"2. File '{output_rdf_additions_file}' sekarang berisi mapping tambahan tersebut dalam format RDF.")
    print("3. Bunda sekarang perlu menggabungkan file ini dengan file reference alignment awal Bunda ('reference_awal.rdf').")
    print("   Cara paling mudah adalah dengan copy-paste bagian <map><Cell>...</Cell></map> dari file ini")
    print("   ke dalam tag <Alignment>...</Alignment> di file reference awal Bunda.")
    print("   Atau, jika keduanya sudah dalam format RDF Alignment yang benar, beberapa tool alignment mungkin punya fitur 'merge alignments'.")