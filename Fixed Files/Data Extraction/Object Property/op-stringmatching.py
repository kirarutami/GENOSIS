import pandas as pd
import rapidfuzz.fuzz
import rapidfuzz.process
import time
import os

# --- Konfigurasi ---
# Ganti dengan path sebenarnya ke file CSV object property Anda
file_op1 = "OP2 MP.csv" # Contoh nama file untuk Ontologi 1 (MP)
file_op2 = "OP2 MCSS.csv" # Contoh nama file untuk Ontologi 2 (MCSS)
prefix_onto1 = "MP" # Prefix untuk Ontologi 1
prefix_onto2 = "MCSS" # Prefix untuk Ontologi 2

# Nama kolom di file CSV input (sesuaikan jika perlu)
subject_col_name = "subject"
op_col_name = "predicate" # Kolom yang akan dicocokkan
object_col_name = "object"
subject_comment_col_name = "subjectComment"
op_comment_col_name = "predicateComment" # Komentar yang akan disertakan
object_comment_col_name = "objectComment"

# Threshold skor kemiripan leksikal (0-100)
lexical_threshold = 80 # Sesuaikan sesuai kebutuhan

# Jumlah maksimum kecocokan yang ditampilkan per object property dari Ontologi 1
limit_per_op = 999

# Nama file CSV untuk output hasil
output_csv_file = f"matched_op_{prefix_onto1}_{prefix_onto2}.csv"

start_time = time.time()

# --- 1. Muat Data dari File CSV ---
print(f"Memuat data object property dari {file_op1} dan {file_op2}...")
try:
    df_op1 = pd.read_csv(file_op1)
    df_op2 = pd.read_csv(file_op2)
    print("Data berhasil dimuat.")
except FileNotFoundError:
    print(f"Error: Pastikan file '{file_op1}' dan '{file_op2}' ada di direktori yang sama atau gunakan path lengkap.")
    exit()
except Exception as e:
    print(f"Error saat memuat file CSV: {e}")
    exit()

# --- Validasi Kolom ---
required_cols = [subject_col_name, op_col_name, object_col_name,
                 subject_comment_col_name, op_comment_col_name, object_comment_col_name]
missing_cols_1 = [col for col in required_cols if col not in df_op1.columns]
missing_cols_2 = [col for col in required_cols if col not in df_op2.columns]

if missing_cols_1:
    print(f"Error: Kolom berikut tidak ditemukan di {file_op1}: {missing_cols_1}")
    print(f"Kolom yang ada: {list(df_op1.columns)}")
    exit()
if missing_cols_2:
    print(f"Error: Kolom berikut tidak ditemukan di {file_op2}: {missing_cols_2}")
    print(f"Kolom yang ada: {list(df_op2.columns)}")
    exit()

# --- 2. Ekstrak Nama Object Property Unik dan Buat Peta Komentar ---
print("Mengekstrak nama object property unik dan membuat peta komentar...")

def create_op_comment_map(df, op_name_col, op_comment_col):
    """Membuat mapping dari nama object property ke komentarnya."""
    comment_map = {}
    # Iterasi per baris untuk mengisi map komentar
    for index, row in df.iterrows():
        op_name = str(row[op_name_col])
        # Ambil komentar dari kolom predicateComment
        op_comment = str(row[op_comment_col]) if pd.notna(row[op_comment_col]) else ""

        # Tambahkan ke map jika nama belum ada (ambil komentar dari kemunculan pertama)
        if op_name and op_name not in comment_map:
            comment_map[op_name] = op_comment

    # Ekstrak juga list nama unik dari kolom predicate
    op_names_list = sorted(df[op_name_col].astype(str).fillna('').unique())
    op_names_list = [name for name in op_names_list if name] # Hapus string kosong

    return op_names_list, comment_map

try:
    # Buat map komentar hanya untuk predicate/object property
    op_names_1, comment_map1 = create_op_comment_map(df_op1, op_col_name, op_comment_col_name)
    op_names_2, comment_map2 = create_op_comment_map(df_op2, op_col_name, op_comment_col_name)

except KeyError as e:
    print(f"Error: Nama kolom ('{op_col_name}' atau '{op_comment_col_name}') tidak ditemukan saat ekstraksi atau pembuatan map: {e}")
    exit()
except Exception as e:
     print(f"Error saat membuat peta komentar object property: {e}")
     exit()

print(f"Jumlah object property unik (non-kosong) di {prefix_onto1}: {len(op_names_1)}")
print(f"Jumlah object property unik (non-kosong) di {prefix_onto2}: {len(op_names_2)}")

# --- 3. Lakukan String Matching dengan RapidFuzz ---
print(f"\nMemulai string matching pada nama object property (kolom '{op_col_name}') (Threshold={lexical_threshold})...")

all_matches = []
# Pre-process daftar target (object property dari Onto 2) untuk efisiensi
processed_op_names_2 = [op.lower() for op in op_names_2]

# Iterasi melalui setiap nama object property unik di Ontologi 1
for op1_name in op_names_1:
    if not op1_name: continue # Lewati jika nama kosong

    # Cari kecocokan terbaik di Ontologi 2
    matches = rapidfuzz.process.extract(
        op1_name.lower(),                # Bandingkan versi lowercase
        processed_op_names_2,            # Dengan list target lowercase
        scorer=rapidfuzz.fuzz.WRatio,    # Scorer pilihan
        score_cutoff=lexical_threshold,  # Filter skor
        limit=limit_per_op               # Batasi hasil
    )

    # matches adalah list of tuples: (matched_string_lower, score, index_in_processed_list)
    for matched_op2_lower, score, index_in_processed in matches:
        # Dapatkan nama object property asli dari Ontologi 2 berdasarkan index
        original_op2_name = op_names_2[index_in_processed]

        # Ambil komentar predicate dari map yang sudah dibuat
        comment1 = comment_map1.get(op1_name, "") # Default string kosong jika tidak ada
        comment2 = comment_map2.get(original_op2_name, "")

        # Simpan hasil kecocokan
        all_matches.append({
            "op_onto1": f"{prefix_onto1}:{op1_name}", # Tambahkan prefix
            "op_onto2": f"{prefix_onto2}:{original_op2_name}",
            "lexical_score": score,
            "comment1": comment1, # Sertakan komentar (predicateComment)
            "comment2": comment2
        })

print(f"Pencocokan selesai. Ditemukan {len(all_matches)} potensi pasangan kecocokan object property.")

# --- 4. Urutkan Hasil dan Siapkan DataFrame ---
if all_matches:
    # Urutkan hasil berdasarkan skor, dari tertinggi ke terendah
    sorted_matches = sorted(all_matches, key=lambda x: x['lexical_score'], reverse=True)

    # Buat DataFrame
    results_df = pd.DataFrame(sorted_matches)

    # Ubah nama kolom sesuai permintaan
    results_df = results_df.rename(columns={
        'op_onto1': 'ont 1',
        'op_onto2': 'ont 2',
        'lexical_score': 'score',
        'comment1': 'Comment Onto 1', # Komentar dari predicateComment Onto 1
        'comment2': 'Comment Onto 2'  # Komentar dari predicateComment Onto 2
    })

    # Bulatkan skor
    results_df['score'] = results_df['score'].round(2)

    # Atur urutan kolom
    output_columns = ['ont 1', 'ont 2', 'score', 'Comment Onto 1', 'Comment Onto 2']
    results_df = results_df[output_columns]

    # --- 5. Simpan Hasil ke File CSV ---
    try:
        results_df.to_csv(output_csv_file, index=False, encoding='utf-8')
        print(f"\n--- Hasil String Matching Object Property (termasuk komentar) disimpan ke: {output_csv_file} ---")
        # Tampilkan head di konsol (mungkin tanpa komentar agar ringkas)
        print("\nContoh beberapa baris hasil teratas:")
        print(results_df[['ont 1', 'ont 2', 'score']].head().to_string(index=False))

    except Exception as e:
        print(f"\nError saat menyimpan hasil ke file CSV: {e}")

else:
    print("\nTidak ditemukan kecocokan object property di atas threshold. Tidak ada file CSV yang dibuat.")

# --- Selesai ---
end_time = time.time()
print(f"\nProses selesai dalam {end_time - start_time:.2f} detik.")