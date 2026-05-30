from sentence_transformers import SentenceTransformer
try:
    SentenceTransformer("FremyCompany/BioLORD-2023-C")
    print("BioLORD-2023-C loaded successfully")
except Exception as e:
    print(f"BioLORD failed ({e}), loading fallback")
    SentenceTransformer("all-MiniLM-L6-v2")
    print("all-MiniLM-L6-v2 loaded successfully")
