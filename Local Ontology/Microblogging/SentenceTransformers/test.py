from sentence_transformers import SentenceTransformer

# 1. Load a pretrained Sentence Transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# The sentences to encode
sentences = [
    "Represents a user in a microblogging platform (e.g., Twitter, Tumblr).",
    "Represents profile customization settings for the user.",
    "Stores the email address associated with the user's account.",
    "Indicates permission to edit profile information.",
    "The primary class representing the user in the system.",
    "Represents the profile of a user, containing personal information such as profile picture, username, and email.",
    "Stores the email address of the user.",
    "Represents the privacy settings related to the user's account, including blocked accounts and story settings.",

]

# 2. Calculate embeddings by calling model.encode()
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# 3. Calculate the embedding similarities
similarities = model.similarity(embeddings, embeddings)
print(similarities)