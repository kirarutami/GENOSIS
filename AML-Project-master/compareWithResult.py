import xml.etree.ElementTree as ET # Untuk parsing XML sederhana
import csv # Untuk membaca dan MENULIS CSV

# --- FUNGSI UNTUK MEMBACA FILE ALIGNMENT RDF/XML SEDERHANA ---
def parse_alignment_rdf(filepath):
    mappings = set() # Gunakan set agar tidak ada duplikat dan pencarian cepat
    parsed_successfully = True
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        # Namespace untuk Alignment API
        ns = {'align': 'http://knowledgeweb.semanticweb.org/heterogeneity/alignment',
              'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
        
        # Cek apakah ada tag <Alignment>
        alignment_tag = root.find('align:Alignment', ns)
        if alignment_tag is None:
            # Mencoba tanpa namespace 'align' jika struktur file sedikit berbeda
            # atau jika namespace default adalah alignment namespace
            alignment_tag = root.find('Alignment')
            if alignment_tag is None and root.tag.endswith("Alignment"): # Jika root adalah tag Alignment
                alignment_tag = root

        if alignment_tag is None:
            print(f"Warning: Tag <Alignment> tidak ditemukan di {filepath}. Mungkin file bukan format alignment standar.")
            # Mencoba mencari <Cell> secara global jika <Alignment> tidak ditemukan
            # Ini kurang ideal tapi bisa jadi fallback jika struktur file sangat sederhana
            cell_elements = root.findall('.//align:Cell', ns)
            if not cell_elements:
                 cell_elements = root.findall('.//Cell') # Mencoba tanpa namespace untuk Cell
        else:
            cell_elements = alignment_tag.findall('.//align:Cell', ns)
            if not cell_elements:
                cell_elements = alignment_tag.findall('.//Cell')


        if not cell_elements:
            print(f"Warning: Tidak ada elemen <Cell> yang ditemukan di dalam {filepath}. File mungkin kosong atau formatnya tidak sesuai.")
            # parsed_successfully = False # Bisa di-set false jika ini dianggap error fatal
            # return mappings, parsed_successfully # Kembalikan status parsing

        for cell_element in cell_elements:
            entity1_el = cell_element.find('align:entity1', ns)
            if entity1_el is None: entity1_el = cell_element.find('entity1') 
            
            entity2_el = cell_element.find('align:entity2', ns)
            if entity2_el is None: entity2_el = cell_element.find('entity2')

            relation_el = cell_element.find('align:relation', ns)
            if relation_el is None: relation_el = cell_element.find('relation')
            
            measure_el = cell_element.find('align:measure', ns)
            if measure_el is None: measure_el = cell_element.find('measure')
            
            if entity1_el is not None and entity2_el is not None and relation_el is not None:
                entity1 = entity1_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                entity2 = entity2_el.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
                relation = relation_el.text
                measure = float(measure_el.text) if measure_el is not None and measure_el.text is not None else 0.0
                
                if relation == '=': # Kita hanya fokus pada relasi kesetaraan untuk reference ini
                     mappings.add((entity1, entity2, relation, measure))
                
    except ET.ParseError as e:
        print(f"Error parsing XML di {filepath}: {e}")
        parsed_successfully = False
    except FileNotFoundError:
        print(f"Error: File alignment '{filepath}' tidak ditemukan.")
        parsed_successfully = False
    except Exception as e_general: # Menangkap error lain yang mungkin terjadi
        print(f"Terjadi error umum saat memproses {filepath}: {e_general}")
        parsed_successfully = False
        
    # Kembalikan mappings dan status keberhasilan parsing
    return mappings, parsed_successfully


# --- FUNGSI UNTUK MENULIS MAPPING BARU KE CSV ---
def write_new_mappings_to_csv(new_mappings_list, output_csv_filepath):
    """
    Menulis daftar mapping baru (yang perlu direview/sudah di-ACC) ke file CSV.
    Setiap mapping adalah tuple: (entity1_local, entity2_genosis, relation, measure_aml)
    """
    if not new_mappings_list:
        print("Tidak ada mapping baru untuk ditulis ke CSV.")
        return

    try:
        with open(output_csv_filepath, mode='w', encoding='utf-8', newline='') as csvfile:
            # Menggunakan titik koma sebagai delimiter
            writer = csv.writer(csvfile, delimiter=';')
            # Menulis header
            writer.writerow(['entity1_local_iri', 'entity2_genosis_iri', 'relation_from_aml', 'measure_from_aml'])
            # Menulis data mapping
            for mapping_data in new_mappings_list:
                writer.writerow(list(mapping_data)) # Konversi tuple ke list untuk writerow
        print(f"File CSV dengan mapping baru berhasil dibuat: '{output_csv_filepath}'")
    except Exception as e:
        print(f"Error saat menulis file CSV: {e}")


# --- CONTOH PENGGUNAAN LOGIKA ---
if __name__ == "__main__":
    # 1. Path ke file-file Bunda (SESUAIKAN!)
    path_reference_awal_bunda = r"D:\thesis\AML-Project-master\reference_alignment_osn_genosis.rdf" 
    path_aml_output = r"D:\thesis\AML-Project-master\store\AML Result for GENOSIS-OSN.rdf"
    
    # Nama file CSV output untuk mapping baru yang akan direview/ditambahkan
    output_csv_for_new_mappings = "aml_new_potential_additions.csv"

    # 2. Baca kedua file alignment
    print(f"Membaca reference alignment awal dari: {path_reference_awal_bunda}")
    ref_mappings, ref_parsed_ok = parse_alignment_rdf(path_reference_awal_bunda)
    
    print(f"Membaca hasil AML dari: {path_aml_output}")
    aml_mappings, aml_parsed_ok = parse_alignment_rdf(path_aml_output)

    if not ref_parsed_ok or not aml_parsed_ok:
        print("Proses dihentikan karena ada error saat membaca salah satu atau kedua file alignment.")
    elif not aml_mappings: # Jika aml_mappings kosong setelah parsing berhasil
        print("Hasil AML kosong atau tidak mengandung mapping yang valid. Tidak ada yang bisa dibandingkan atau ditambahkan.")
    else:
        print(f"\nJumlah mapping di reference awal Bunda: {len(ref_mappings)}")
        print(f"Jumlah mapping di hasil AML (dengan relasi '='): {len([m for m in aml_mappings if m[2] == '='])}")

        # 3. Temukan mapping 100% dari AML dengan relasi '=' yang belum ada di reference Bunda
        # Kita hanya peduli entity1, entity2, dan relation='=' untuk perbandingan
        # karena reference awal Bunda juga hanya berisi relasi '=' dari anotasi.
        ref_pairs_only = set([(m[0], m[1]) for m in ref_mappings if m[2] == '=']) # Hanya pasangan (e1, e2) dari reference
        
        new_potential_mappings_for_review_data = [] # Untuk disimpan ke CSV
        
        for aml_map_data in aml_mappings:
            aml_e1, aml_e2, aml_rel, aml_measure = aml_map_data
            
            # Fokus pada yang 100% (atau >=1.0) dan relasi ekivalen ('=')
            if aml_measure >= 1.0 and aml_rel == '=':
                # Cek apakah pasangan (aml_e1, aml_e2) belum ada di reference awal
                # Asumsi: entity1 di AML adalah local, entity2 adalah global (atau sebaliknya, perlu konsisten)
                # Ini perlu disesuaikan dengan urutan <onto1> dan <onto2> di file output AML Bunda
                # Jika <onto1> adalah OSN Lokal dan <onto2> adalah GENOSIS di file AML:
                # maka aml_e1 adalah lokal, aml_e2 adalah GENOSIS.
                # Pasangan di ref_pairs_only juga (lokal, GENOSIS).
                if (aml_e1, aml_e2) not in ref_pairs_only:
                    new_potential_mappings_for_review_data.append(aml_map_data) # Simpan tuple lengkapnya

        print(f"\nJumlah mapping 100% dari AML dengan relasi '=' yang BARU (belum ada di reference awal): {len(new_potential_mappings_for_review_data)}")
        
        if new_potential_mappings_for_review_data:
            print("Mapping baru yang berpotensi ditambahkan (akan ditulis ke CSV untuk review Bunda):")
            for i, new_map_data in enumerate(new_potential_mappings_for_review_data):
                print(f"  {i+1}. Lokal: {new_map_data[0]} | GENOSIS: {new_map_data[1]} | Rel: {new_map_data[2]} | Score: {new_map_data[3]}")
            
            # Tulis mapping baru ini ke file CSV
            write_new_mappings_to_csv(new_potential_mappings_for_review_data, output_csv_for_new_mappings)
            
            print("\nLANGKAH SELANJUTNYA BUAT BUNDA (SETELAH INI):")
            print(f"1. REVIEW file '{output_csv_for_new_mappings}'. Pastikan semua mapping di dalamnya memang BENAR dan ingin Bunda tambahkan.")
            print(f"2. Jika sudah yakin, Bunda bisa gunakan file CSV tersebut dengan SCRIPT PYTHON SEBELUMNYA ('create_new_aml_rdf_from_approved')")
            print(f"   untuk membuat file RDF alignment baru (misalnya 'aml_additions_reference.rdf').")
            print(f"3. Kemudian, gabungkan isi file 'aml_additions_reference.rdf' ini ke file reference alignment utama Bunda.")
        else:
            print("Tidak ada mapping 100% baru dari AML dengan relasi '=' yang belum ada di reference awal Bunda.")