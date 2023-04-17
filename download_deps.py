from sentence_transformers import SentenceTransformer
# from src.config import LABSE_PATH
LABSE_PATH = 'sentence-transformers/LaBSE'
model = SentenceTransformer(LABSE_PATH, device='cpu')

import nltk
nltk.download("punkt")
