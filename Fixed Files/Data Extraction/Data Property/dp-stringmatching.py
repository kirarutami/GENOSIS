import pandas as pd
import rapidfuzz.fuzz
import rapidfuzz.process
import time
import os

# --- Konfigurasi ---
# Ganti dengan path sebenarnya ke file CSV data property Anda
file_dp1 = "DP2 MCSS.csv" # Contoh nama file untuk Ontologi 1 (MCSS)
file_dp2 = "DP2 OFB.csv" # Contoh nama file untuk Ontologi 2 (OFB)
prefix_onto1 = "MCSS" # Prefix untuk Ontologi 1
prefix_onto2 = "OFB" # Prefix untuk Ontologi 2

# Nama kolom di file CSV input (sesuaikan jika perlu)
dp_col_name = "dataProperty"
dp_comment_col_name = "dataPropertyComment"
# Kolom lain yang perlu ada untuk validasi (meski tidak langsung dipakai untuk matching)
class_col_name = "class"
class_comment_col = "classComment"

# Threshold skor kemiripan leksikal (0-100)
lexical_threshold = 80 # Sesuaikan sesuai kebutuhan

# Jumlah maksimum kecocokan yang ditampilkan per data property dari Ontologi 1
limit_per_dp = 999

# Nama file CSV untuk output hasil
output_csv_file = f"matched_dp_{prefix_onto1}_{prefix_onto2}.csv"

start_time = time.time()

# --- 1. Muat Data dari File CSV ---
print(f"Memuat data property dari {file_dp1} dan {file_dp2}...")
try:
    df_dp1 = pd.read_csv(file_dp1)
    df_dp2 = pd.read_csv(file_dp2)
    print("Data berhasil dimuat.")
except FileNotFoundError:
    print(f"Error: Pastikan file '{file_dp1}' dan '{file_dp2}' ada di direktori yang sama atau gunakan path lengkap.")
    exit()
except Exception as e:
    print(f"Error saat memuat file CSV: {e}")
    exit()

# --- Validasi Kolom ---
required_cols = [class_col_name, dp_col_name, class_comment_col, dp_comment_col_name]
missing_cols_1 = [col for col in required_cols if col not in df_dp1.columns]
missing_cols_2 = [col for col in required_cols if col not in df_dp2.columns]

if missing_cols_1:
    print(f"Error: Kolom berikut tidak ditemukan di {file_dp1}: {missing_cols_1}")
    print(f"Kolom yang ada: {list(df_dp1.columns)}")
    exit()
if missing_cols_2:
    print(f"Error: Kolom berikut tidak ditemukan di {file_dp2}: {missing_cols_2}")
    print(f"Kolom yang ada: {list(df_dp2.columns)}")
    exit()

# --- 2. Ekstrak Nama Data Property Unik dan Buat Peta Komentar ---
print("Mengekstrak nama data property unik dan membuat peta komentar...")

def create_dp_comment_map(df, dp_name_col, dp_comment_col):
    """Membuat mapping dari nama data property ke komentarnya."""
    comment_map = {}
    # Iterasi per baris untuk mengisi map komentar
    for index, row in df.iterrows():
        dp_name = str(row[dp_name_col])
        dp_comment = str(row[dp_comment_col]) if pd.notna(row[dp_comment_col]) else ""

        # Tambahkan ke map jika nama belum ada (ambil komentar dari kemunculan pertama)
        if dp_name and dp_name not in comment_map:
            comment_map[dp_name] = dp_comment

    # Ekstrak juga list nama unik
    dp_names_list = sorted(df[dp_name_col].astype(str).fillna('').unique())
    dp_names_list = [name for name in dp_names_list if name] # Hapus string kosong

    return dp_names_list, comment_map

try:
    dp_names_1, comment_map1 = create_dp_comment_map(df_dp1, dp_col_name, dp_comment_col_name)
    dp_names_2, comment_map2 = create_dp_comment_map(df_dp2, dp_col_name, dp_comment_col_name)

except KeyError as e:
    print(f"Error: Nama kolom ('{dp_col_name}' atau '{dp_comment_col_name}') tidak ditemukan saat ekstraksi atau pembuatan map: {e}")
    exit()
except Exception as e:
     print(f"Error saat membuat peta komentar data property: {e}")
     exit()

print(f"Jumlah data property unik (non-kosong) di {prefix_onto1}: {len(dp_names_1)}")
print(f"Jumlah data property unik (non-kosong) di {prefix_onto2}: {len(dp_names_2)}")

# --- 3. Lakukan String Matching dengan RapidFuzz ---
print(f"\nMemulai string matching pada nama data property (Threshold={lexical_threshold})...")

all_matches = []
# Pre-process daftar target (data property dari Onto 2) untuk efisiensi
processed_dp_names_2 = [dp.lower() for dp in dp_names_2]

# Iterasi melalui setiap nama data property unik di Ontologi 1
for dp1_name in dp_names_1:
    if not dp1_name: continue # Seharusnya sudah dieliminasi

    # Cari kecocokan terbaik di Ontologi 2
    matches = rapidfuzz.process.extract(
        dp1_name.lower(),                # Bandingkan versi lowercase
        processed_dp_names_2,            # Dengan list target lowercase
        scorer=rapidfuzz.fuzz.WRatio,    # Scorer pilihan
        score_cutoff=lexical_threshold,  # Filter skor
        limit=limit_per_dp               # Batasi hasil
    )

    # matches adalah list of tuples: (matched_string_lower, score, index_in_processed_list)
    for matched_dp2_lower, score, index_in_processed in matches:
        # Dapatkan nama data property asli dari Ontologi 2 berdasarkan index
        original_dp2_name = dp_names_2[index_in_processed]

        # Ambil komentar dari map yang sudah dibuat
        comment1 = comment_map1.get(dp1_name, "") # Default string kosong jika tidak ada
        comment2 = comment_map2.get(original_dp2_name, "")

        # Simpan hasil kecocokan
        all_matches.append({
            "dp_onto1": f"{prefix_onto1}:{dp1_name}", # Tambahkan prefix
            "dp_onto2": f"{prefix_onto2}:{original_dp2_name}",
            "lexical_score": score,
            "comment1": comment1, # Sertakan komentar
            "comment2": comment2
        })

print(f"Pencocokan selesai. Ditemukan {len(all_matches)} potensi pasangan kecocokan data property.")

# --- 4. Urutkan Hasil dan Siapkan DataFrame ---
if all_matches:
    # Urutkan hasil berdasarkan skor, dari tertinggi ke terendah
    sorted_matches = sorted(all_matches, key=lambda x: x['lexical_score'], reverse=True)

    # Buat DataFrame
    results_df = pd.DataFrame(sorted_matches)

    # Ubah nama kolom sesuai permintaan
    results_df = results_df.rename(columns={
        'dp_onto1': 'ont 1',
        'dp_onto2': 'ont 2',
        'lexical_score': 'score',
        'comment1': 'Comment Onto 1',
        'comment2': 'Comment Onto 2'
    })

    # Bulatkan skor
    results_df['score'] = results_df['score'].round(2)

    # Atur urutan kolom
    output_columns = ['ont 1', 'ont 2', 'score', 'Comment Onto 1', 'Comment Onto 2']
    results_df = results_df[output_columns]

    # --- 5. Simpan Hasil ke File CSV ---
    try:
        results_df.to_csv(output_csv_file, index=False, encoding='utf-8')
        print(f"\n--- Hasil String Matching Data Property (termasuk komentar) disimpan ke: {output_csv_file} ---")
        # Tampilkan head di konsol (mungkin tanpa komentar agar ringkas)
        print("\nContoh beberapa baris hasil teratas:")
        print(results_df[['ont 1', 'ont 2', 'score']].head().to_string(index=False))

    except Exception as e:
        print(f"\nError saat menyimpan hasil ke file CSV: {e}")

else:
    print("\nTidak ditemukan kecocokan data property di atas threshold. Tidak ada file CSV yang dibuat.")

# --- Selesai ---
end_time = time.time()
print(f"\nProses selesai dalam {end_time - start_time:.2f} detik.")