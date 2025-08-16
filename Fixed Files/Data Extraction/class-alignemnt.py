import pandas as pd
from rapidfuzz import fuzz, process

# Definisi fungsi pencocokan dengan token_set_ratio
def match_columns_with_token_ratio(col1, col2, threshold=80):
    matches = []
    for item1 in col1:
        best_match = process.extractOne(item1, col2, scorer=fuzz.token_set_ratio)
        if best_match and best_match[1] >= threshold:
            matches.append((item1, best_match[0], best_match[1]))
    return matches

# Data sample untuk 'class' dan 'subClass'
o1_classes = ['User', 'ContentCreation', 'Reels']
o2_classes = ['LiveSpacesRooms', 'UpcomingSessions']

o1_subclasses = ['AdminUser', 'RegularUser', 'ShortVideoReels']
o2_subclasses = ['HostUser', 'GuestUser']

# Matching class and subclass
class_matches = match_columns_with_token_ratio(o1_classes, o2_classes)
subclass_matches = match_columns_with_token_ratio(o1_subclasses, o2_subclasses)

# Membuat DataFrame untuk hasil pencocokan class dan subclass
class_subclass_results = {
    'Type': ['Class'] * len(class_matches) + ['SubClass'] * len(subclass_matches),
    'Item_O1': [match[0] for match in class_matches + subclass_matches],
    'Item_O2': [match[1] for match in class_matches + subclass_matches],
    'Similarity': [match[2] for match in class_matches + subclass_matches]
}

class_subclass_df = pd.DataFrame(class_subclass_results)

# Menyimpan hasil ke CSV
output_class_path = 'class_subclass_alignment_results.csv'
class_subclass_df.to_csv(output_class_path, index=False)

import ace_tools as tools; tools.display_dataframe_to_user(name="Class and SubClass Alignment Results", dataframe=class_subclass_df)
