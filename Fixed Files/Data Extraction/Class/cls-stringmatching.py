import pandas as pd
import rapidfuzz.fuzz
import rapidfuzz.process
import time
import os

# --- Konfigurasi ---
# Path ke file CSV hasil ekstraksi kelas Anda
file_cls1 = "CLS MCSS.csv"
file_cls2 = "CLS OFB.csv"

# Nama kolom kelas dan subkelas (sesuaikan jika perlu)
class_col_name = "class"
subclass_col_name = "subClass"

# *** BARU: Nama kolom komentar (sesuaikan jika perlu) ***
class_comment_col = "classComment"
subclass_comment_col = "subClassComment"

# Threshold skor kemiripan leksikal (0-100)
lexical_threshold = 80

# Jumlah maksimum kecocokan yang ditampilkan per kelas dari Ontologi 1
limit_per_class = 999

# Nama file CSV untuk output hasil
output_csv_file = "MCSS-OFB class matching.csv" # Nama file output baru

start_time = time.time()

# --- 1. Muat Data dari File CSV ---
print(f"Memuat data kelas dari {file_cls1} dan {file_cls2}...")
try:
    df_cls1 = pd.read_csv(file_cls1)
    df_cls2 = pd.read_csv(file_cls2)
    print("Data berhasil dimuat.")
except FileNotFoundError:
    print(f"Error: Pastikan file '{file_cls1}' dan '{file_cls2}' ada di direktori yang sama atau gunakan path lengkap.")
    exit()
except Exception as e:
    print(f"Error saat memuat file CSV: {e}")
    exit()

# --- Validasi Kolom (Termasuk Kolom Komentar) ---
required_cols_1 = [class_col_name, subclass_col_name, class_comment_col, subclass_comment_col]
required_cols_2 = [class_col_name, subclass_col_name, class_comment_col, subclass_comment_col]
missing_cols_1 = [col for col in required_cols_1 if col not in df_cls1.columns]
missing_cols_2 = [col for col in required_cols_2 if col not in df_cls2.columns]

if missing_cols_1:
    print(f"Error: Kolom berikut tidak ditemukan di {file_cls1}: {missing_cols_1}")
    print(f"Kolom yang ada: {list(df_cls1.columns)}")
    exit()
if missing_cols_2:
    print(f"Error: Kolom berikut tidak ditemukan di {file_cls2}: {missing_cols_2}")
    print(f"Kolom yang ada: {list(df_cls2.columns)}")
    exit()

# --- 2. Ekstrak Nama Kelas Unik dan Buat Peta Komentar ---
print("Mengekstrak nama kelas unik dan membuat peta komentar...")

def create_class_comment_map(df, class_col, subclass_col, class_comment_c, subclass_comment_c):
    """Membuat mapping dari nama kelas ke komentarnya."""
    comment_map = {}
    # Iterasi per baris untuk mengisi map komentar
    for index, row in df.iterrows():
        class_name = str(row[class_col])
        subclass_name = str(row[subclass_col])
        class_comment = str(row[class_comment_c]) if pd.notna(row[class_comment_c]) else ""
        subclass_comment = str(row[subclass_comment_c]) if pd.notna(row[subclass_comment_c]) else ""

        # Tambahkan ke map jika nama belum ada (ambil komentar dari kemunculan pertama)
        if class_name and class_name not in comment_map:
            comment_map[class_name] = class_comment
        if subclass_name and subclass_name not in comment_map:
            comment_map[subclass_name] = subclass_comment
            
    # Ekstrak juga list nama unik seperti sebelumnya
    names = pd.concat([df[class_col], df[subclass_col]]) \
              .astype(str).fillna('').unique().tolist()
    class_names_list = sorted([name for name in names if name])

    return class_names_list, comment_map

try:
    class_names_1, comment_map1 = create_class_comment_map(df_cls1, class_col_name, subclass_col_name, class_comment_col, subclass_comment_col)
    class_names_2, comment_map2 = create_class_comment_map(df_cls2, class_col_name, subclass_col_name, class_comment_col, subclass_comment_col)

except KeyError as e:
    print(f"Error: Nama kolom tidak ditemukan saat ekstraksi atau pembuatan map: {e}")
    exit()
except Exception as e:
     print(f"Error saat membuat peta komentar: {e}")
     exit()


print(f"Jumlah kelas unik (non-kosong) di Onto1: {len(class_names_1)}")
print(f"Jumlah kelas unik (non-kosong) di Onto2: {len(class_names_2)}")

# --- 3. Lakukan String Matching dengan RapidFuzz ---
print(f"\nMemulai string matching pada nama kelas (Threshold={lexical_threshold})...")

all_matches = []
processed_class_names_2 = [cls.lower() for cls in class_names_2]

for class1_name in class_names_1:
    if not class1_name: continue

    matches = rapidfuzz.process.extract(
        class1_name.lower(),
        processed_class_names_2,
        scorer=rapidfuzz.fuzz.WRatio,
        score_cutoff=lexical_threshold,
        limit=limit_per_class
    )

    for matched_class2_lower, score, index_in_processed in matches:
        original_class2_name = class_names_2[index_in_processed]

        # *** BARU: Ambil komentar dari map ***
        comment1 = comment_map1.get(class1_name, "") # Default string kosong jika tidak ada
        comment2 = comment_map2.get(original_class2_name, "")

        all_matches.append({
            "class_onto1": "MCSS:" + class1_name,
            "class_onto2": "OFB:" + original_class2_name,
            "lexical_score": score,
            "comment1": "MCSS:" + comment1, # Tambahkan komentar ke hasil
            "comment2":"OFB:" +  comment2
        })

print(f"Pencocokan selesai. Ditemukan {len(all_matches)} potensi pasangan kecocokan kelas.")

# --- 4. Urutkan Hasil dan Siapkan DataFrame ---
if all_matches:
    sorted_matches = sorted(all_matches, key=lambda x: x['lexical_score'], reverse=True)
    results_df = pd.DataFrame(sorted_matches)

    # *** BARU: Ubah nama kolom (termasuk kolom komentar) ***
    results_df = results_df.rename(columns={
        'class_onto1': 'ont 1',
        'class_onto2': 'ont 2',
        'lexical_score': 'score',
        'comment1': 'Comment Onto 1', # Nama kolom baru untuk komentar
        'comment2': 'Comment Onto 2'
    })

    # (Opsional) Bulatkan skor
    results_df['score'] = results_df['score'].round(2)

    # *** BARU: Pastikan urutan kolom sesuai keinginan ***
    output_columns = ['ont 1', 'ont 2', 'score', 'Comment Onto 1', 'Comment Onto 2']
    results_df = results_df[output_columns]


    # --- 5. Simpan Hasil ke File CSV ---
    try:
        results_df.to_csv(output_csv_file, index=False, encoding='utf-8')
        print(f"\n--- Hasil String Matching Kelas (termasuk komentar) disimpan ke: {output_csv_file} ---")
        # Tampilkan head, mungkin tanpa komentar agar tidak terlalu lebar di konsol
        print("\nContoh beberapa baris hasil teratas (tanpa komentar di pratinjau ini):")
        print(results_df[['ont 1', 'ont 2', 'score']].head().to_string(index=False))

    except Exception as e:
        print(f"\nError saat menyimpan hasil ke file CSV: {e}")

else:
    print("\nTidak ditemukan kecocokan kelas di atas threshold. Tidak ada file CSV yang dibuat.")

# --- Selesai ---
end_time = time.time()
print(f"\nProses selesai dalam {end_time - start_time:.2f} detik.")