import pandas as pd
import networkx as nx
import time

# --- Konfigurasi ---
# Nama file CSV yang berisi gabungan semua hasil pairwise matching OBJECT PROPERTY
combined_matches_file = "matched-op.csv" # GANTI JIKA PERLU

# Nama kolom di file CSV input (sesuaikan jika output script sebelumnya berbeda)
col_element1 = "ont 1"
col_element2 = "ont 2"
col_score = "score"
col_comment1 = "Comment Onto 1" # Komentar dari predicateComment asli
col_comment2 = "Comment Onto 2" # Komentar dari predicateComment asli

# Threshold skor minimum untuk dianggap sebagai hubungan/edge dalam graf
graph_threshold = 80.0 # Sesuaikan sesuai kebutuhan

# Nama file output untuk hasil kelompok kesetaraan object property
output_groups_file = "op_equivalence_groups_with_comments.txt" # Nama file output spesifik OP

start_time = time.time()

# --- 1. Muat Data Gabungan (Termasuk Komentar) ---
print(f"Memuat data gabungan object property dari {combined_matches_file}...")
try:
    df_combined = pd.read_csv(combined_matches_file)

    # Validasi kolom yang diperlukan
    required_cols = [col_element1, col_element2, col_score, col_comment1, col_comment2]
    missing_cols = [col for col in required_cols if col not in df_combined.columns]
    if missing_cols:
        print(f"Error: Kolom berikut tidak ditemukan di {combined_matches_file}: {missing_cols}")
        print(f"Pastikan file gabungan Anda ('{combined_matches_file}') memiliki kolom yang benar.")
        print(f"Kolom yang ada: {list(df_combined.columns)}")
        exit()

    # Pastikan kolom skor adalah numerik & tangani error/NaN
    df_combined[col_score] = pd.to_numeric(df_combined[col_score], errors='coerce')
    df_combined.dropna(subset=[col_score], inplace=True)

    # Isi komentar yang kosong/NaN dengan string kosong
    df_combined[col_comment1] = df_combined[col_comment1].fillna("")
    df_combined[col_comment2] = df_combined[col_comment2].fillna("")

    print(f"Data berhasil dimuat. Jumlah baris (setelah cleanup skor): {len(df_combined)}")

except FileNotFoundError:
    print(f"Error: File '{combined_matches_file}' tidak ditemukan.")
    exit()
except KeyError as e:
     print(f"Error: Kolom yang diperlukan tidak ditemukan saat validasi: {e}")
     exit()
except Exception as e:
    print(f"Error saat memuat atau memproses file CSV: {e}")
    exit()

# --- 2. Buat Peta Komentar Global untuk Object Property ---
# Membuat dictionary untuk menyimpan komentar (predicateComment) setiap OP unik
print("Membuat peta komentar global untuk object property...")
element_comment_map = {}
for index, row in df_combined.iterrows():
    e1_id = str(row[col_element1]) # ID unik OP Onto 1 (misal: MCSS:canEditProfile)
    e2_id = str(row[col_element2]) # ID unik OP Onto 2 (misal: OFB:editUserProfile)
    c1 = str(row[col_comment1])    # Komentar OP 1 (dari predicateComment asli)
    c2 = str(row[col_comment2])    # Komentar OP 2 (dari predicateComment asli)

    # Simpan komentar jika elemen belum ada di map (ambil dari kemunculan pertama)
    if e1_id not in element_comment_map:
        element_comment_map[e1_id] = c1
    if e2_id not in element_comment_map:
        element_comment_map[e2_id] = c2

print(f"Peta komentar dibuat untuk {len(element_comment_map)} object property unik.")

# --- 3. Bangun Graf Keterhubungan ---
print(f"Membangun graf keterhubungan object property (menggunakan skor >= {graph_threshold})...")
G = nx.Graph()

# Iterasi melalui setiap baris (kecocokan pairwise) di DataFrame
for index, row in df_combined.iterrows():
    score = row[col_score]
    element1 = str(row[col_element1])
    element2 = str(row[col_element2])

    # Hanya tambahkan edge jika skor memenuhi threshold
    if score >= graph_threshold:
        G.add_edge(element1, element2, weight=score)

print(f"Graf dibangun. Jumlah node (OP unik): {G.number_of_nodes()}, Jumlah edge (hubungan valid): {G.number_of_edges()}")

# --- 4. Temukan Kelompok Kesetaraan (Connected Components) ---
print("Mencari kelompok kesetaraan object property...")
equivalence_groups_sets = list(nx.connected_components(G))
print(f"Ditemukan {len(equivalence_groups_sets)} kelompok kesetaraan object property.")

# --- 5. Tampilkan dan Simpan Hasil Kelompok Kesetaraan (dengan Komentar) ---
if equivalence_groups_sets:
    print(f"\n--- Kelompok Kesetaraan Object Property Ditemukan (disimpan ke {output_groups_file}) ---")
    sorted_groups = sorted(equivalence_groups_sets, key=len, reverse=True)

    try:
        with open(output_groups_file, "w", encoding="utf-8") as f:
            for i, group_set in enumerate(sorted_groups):
                # Hanya proses/tampilkan grup yang berisi lebih dari 1 elemen
                if len(group_set) > 1:
                    group_header = f"\nKelompok OP #{i+1} (Ukuran: {len(group_set)}):" # Label OP
                    print(group_header) # Tampilkan di konsol
                    f.write(group_header + "\n") # Tulis ke file

                    sorted_group_list = sorted(list(group_set))
                    for element_id in sorted_group_list:
                        # Ambil komentar dari peta
                        comment = element_comment_map.get(element_id, "[Komentar tidak ditemukan]")
                        output_line = f"  - {element_id}: {comment}"
                        print(output_line) # Tampilkan di konsol
                        f.write(output_line + "\n") # Tulis ke file
                    f.write("\n") # Beri jarak antar grup di file
        print(f"\nHasil kelompok kesetaraan object property (termasuk komentar) berhasil disimpan ke {output_groups_file}")
    except Exception as e:
        print(f"\nError saat menyimpan hasil ke file teks: {e}")

else:
    print("\nTidak ditemukan kelompok kesetaraan object property (tidak ada elemen yang terhubung berdasarkan threshold).")

# --- Selesai ---
end_time = time.time()
print(f"\nAnalisis dan sintesis object property selesai dalam {end_time - start_time:.2f} detik.")