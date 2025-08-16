import pandas as pd
from rapidfuzz import fuzz, process
import re

# Membaca file CSV
o1 = pd.read_csv('DP OSN.csv', delimiter=',')
o2 = pd.read_csv('OP OSN.csv', delimiter=',')

# Fungsi untuk memecah string camelCase atau PascalCase menjadi token-token
def tokenize_string(s):
    if pd.isna(s):
        return []  # Kembalikan list kosong jika nilai NaN
    return re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', str(s))

# Fungsi untuk mencocokkan dua kolom dengan token_set_ratio setelah tokenisasi
def match_columns_with_tokenized_ratio(col1, col2, threshold=80):
    matches = []
    tokenized_col1 = [" ".join(tokenize_string(item)) for item in col1]
    tokenized_col2 = [" ".join(tokenize_string(item)) for item in col2]
    
    for tokenized_item1 in tokenized_col1:
        best_match = process.extractOne(tokenized_item1, tokenized_col2, scorer=fuzz.token_set_ratio)
        if best_match and best_match[1] >= threshold:
            matches.append((tokenized_item1, best_match[0], best_match[1]))
    return matches

# Pencocokan subject, predicate, object
subject_matches = match_columns_with_tokenized_ratio(o1['Subject'], o2['Subject'])
predicate_matches = match_columns_with_tokenized_ratio(o1['Predicate'], o2['Predicate'])
object_matches = match_columns_with_tokenized_ratio(o1['Object'], o2['Object'])

# Pencocokan komentar untuk analisis lebih lanjut
subject_comment_matches = match_columns_with_tokenized_ratio(o1['subjectComment'], o2['subjectComment'])
predicate_comment_matches = match_columns_with_tokenized_ratio(o1['predicateComment'], o2['predicateComment'])
object_comment_matches = match_columns_with_tokenized_ratio(o1['objectComment'], o2['objectComment'])

# Membuat DataFrame untuk hasil pencocokan
alignment_results = {
    'Type': ['Subject'] * len(subject_matches) + ['Predicate'] * len(predicate_matches) + ['Object'] * len(object_matches) +
            ['SubjectComment'] * len(subject_comment_matches) + ['PredicateComment'] * len(predicate_comment_matches) + ['ObjectComment'] * len(object_comment_matches),
    'Item_O1': [match[0] for match in subject_matches + predicate_matches + object_matches + 
                subject_comment_matches + predicate_comment_matches + object_comment_matches],
    'Item_O2': [match[1] for match in subject_matches + predicate_matches + object_matches + 
                subject_comment_matches + predicate_comment_matches + object_comment_matches],
    'Similarity': [match[2] for match in subject_matches + predicate_matches + object_matches + 
                   subject_comment_matches + predicate_comment_matches + object_comment_matches]
}

results_df = pd.DataFrame(alignment_results)

# Menyimpan hasil ke CSV
results_df.to_csv('OSN_ontology_alignment_tokenized_ratio_results.csv', index=False)

print("Hasil pencocokan disimpan dalam 'ontology_alignment_tokenized_ratio_results.csv'")
