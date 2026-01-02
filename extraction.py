# extraction.py

from PyPDF2 import PdfReader
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------
# Extract PDF text
# ---------------------------
def extract_pdf_text(pdf_file) -> str:
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


# ---------------------------
# Clean text
# ---------------------------
def clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = [l.strip() for l in lines if len(l.strip()) > 5]
    return "\n".join(cleaned)


# ---------------------------
# Split syllabus into units
# ---------------------------
def split_units(syllabus_text: str) -> dict:
    parts = re.split(r"(UNIT\s+[IVX]+)", syllabus_text, flags=re.IGNORECASE)
    units = {}
    for i in range(1, len(parts), 2):
        units[parts[i].upper()] = parts[i + 1]
    return units


# ---------------------------
# Chunk book text
# ---------------------------
def chunk_text(text, chunk_size=400):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks


# ---------------------------
# Map syllabus unit → book content
# ---------------------------
def map_syllabus_to_book(syllabus_units: dict, book_text: str) -> dict:
    model = SentenceTransformer("all-MiniLM-L6-v2")

    book_chunks = chunk_text(book_text)
    book_embeddings = model.encode(book_chunks)

    mapped = {}

    for unit, unit_text in syllabus_units.items():
        unit_embedding = model.encode([unit_text])
        sims = cosine_similarity(unit_embedding, book_embeddings)[0]

        top_idx = np.argsort(sims)[-5:]
        mapped_chunks = [book_chunks[i] for i in top_idx]

        mapped[unit] = "\n".join(mapped_chunks)

    return mapped
