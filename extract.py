import spacy
import re
import json
import time
from difflib import SequenceMatcher

global best_score

# -------------------------------------------------------
# Load spaCy English model
# -------------------------------------------------------
nlp = spacy.load("en_core_web_sm")

# -------------------------------------------------------
# Load Recipient DB
# -------------------------------------------------------
def load_db(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["recipients"]

# -------------------------------------------------------
# Extract PERSON (spaCy + fallback)
# -------------------------------------------------------
def extract_person(text):
    doc = nlp(text)

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.lower()

    words = text.split()
    candidates = []

    skip_words = {
        "main", "street", "roseville", "francisco", "united",
        "states", "ca", "usa", "lbs", "fat1"
    }

    for i in range(len(words) - 1):
        w1 = words[i]
        w2 = words[i + 1]

        if not w1.isalpha() or not w2.isalpha():
            continue
        if w1.lower() in skip_words or w2.lower() in skip_words:
            continue

        pair = f"{w1} {w2}".lower()
        candidates.append(pair)

    return candidates[-1] if candidates else None

# -------------------------------------------------------
# Extract ADDRESS
# -------------------------------------------------------
def extract_address(text):
    pattern = r"\d{2,5}\s+[A-Za-z0-9\s]+?(?:dr|st|road|ave|blvd|street)\b.*?(?:\d{5}(?:-\d{4})?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return None

# -------------------------------------------------------
# Compare strings
# -------------------------------------------------------
def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# -------------------------------------------------------
# Match extracted name/address with DB
# -------------------------------------------------------
def find_best_match(extracted_name, extracted_address, db):
    if not extracted_name:
        return None

    best = None
    best_score = 0

    for r in db:
        db_name = f"{r['first_name']} {r['last_name']}".lower()
        db_addr = r["address"].lower()

        name_score = similarity(extracted_name, db_name)
        addr_score = similarity(extracted_address or "", db_addr)

        final_score = (name_score * 0.7) + (addr_score * 0.3)
        
        if final_score > best_score:
            best_score = final_score
            print("BEST SCORE:", best_score)
            print("Extracted Name11:", db_name)
            best = r

    if best_score < 0.50:
        return None

    return best
# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":

    db_file = "recipient_db.json"
    db = load_db(db_file)

    ocr_inputs = [
        "lex2 2.8 lbs 2821 carradale dr 95661-4047 roseville ca fat1 united states zoey dong dsm1",
        "sample 123 main street 94105 san francisco ca john doe usa"
    ]

    total_time = 0  # To calculate average

    for i, text in enumerate(ocr_inputs, 1):
        print(f"\n--- OCR RECORD {i} ---")
        print("OCR Text:", text)

        start_time = time.time()

        extracted_name = extract_person(text)
        extracted_address = extract_address(text)
        match = find_best_match(extracted_name, extracted_address, db)

        end_time = time.time()
        elapsed = end_time - start_time
        total_time += elapsed

        print("Extracted Name:", extracted_name)
        print("Extracted Address:", extracted_address)

        print(f"Time Taken for Record {i}: {elapsed:.4f} seconds")

        print("\n--- MATCH RESULT ---")
        if match:
            print("Matched Recipient ID:", match["recipient_id"])
            print("Matched Name:", match["preferred_full_name"])
            print("Matched Full Address:", match["address"])
        else:
            print("No match found")

    avg_time = total_time / len(ocr_inputs)
    print("\n==============================")
    print("Average Time per Record:", avg_time, "seconds")
    print("==============================")