import requests
import json
import re
import time

# =============================================
# OLLAMA CONFIG
# =============================================
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma:2b"

# =============================================
# SYSTEM PROMPT (ADDRESS ONLY)
# =============================================
SYSTEM_PROMPT = """
You are an OCR address normalization system.

Extract ONLY the SINGLE BEST DELIVERY ADDRESS.

Rules:
- Ignore weights, labels, countries, tracking
- Remove noise like "lbs", "priority", "fedex", "ups"
- Address MUST contain street + city + state + ZIP
- Correct OCR spelling mistakes
- Standardize format

Return STRICT JSON only.

Format:
{
  "recipient_address": ""
}
"""

# =============================================
# CLEAN OCR TEXT (FOR ADDRESS)
# =============================================
def clean_ocr(text):
    text = text.lower()
    text = re.sub(r"\b\d+(\.\d+)?\s?lbs\b", "", text)
    text = re.sub(r"\b(united states|usa)\b", "", text)
    text = re.sub(r"\b(priority|ground|shipping|ship to|from|fedex|ups|usps)\b", "", text)
    return re.sub(r"\s+", " ", text).strip()

# =============================================
# NAME EXTRACTION (LOWERCASE SAFE)
# =============================================
def extract_name(text):
    text = text.lower()

    # Common non-name words
    stopwords = {
        "ship", "to", "from", "priority", "mail", "ground",
        "united", "states", "usa", "fedex", "ups", "usps",
        "roseville", "ca", "blvd", "drive", "dr", "street",
        "st", "parkway", "pkwy", "lane", "ln", "suite", "ste"
    }

    words = re.findall(r"[a-z]+", text)

    candidates = []
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]

        if w1 in stopwords or w2 in stopwords:
            continue

        # Optional 3rd word
        if i + 2 < len(words) and words[i + 2] not in stopwords:
            candidates.append(f"{w1} {w2} {words[i+2]}")
        else:
            candidates.append(f"{w1} {w2}")

    if not candidates:
        return ""

    # Prefer last candidate (names usually near address)
    name = candidates[-1]

    return " ".join(w.capitalize() for w in name.split())

# =============================================
# CALL OLLAMA
# =============================================
def call_ollama(text):
    payload = {
        "model": MODEL_NAME,
        "prompt": SYSTEM_PROMPT + "\nOCR TEXT:\n" + text,
        "stream": False,
        "options": {"temperature": 0}
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["response"]

# =============================================
# EXTRACT JSON
# =============================================
def extract_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except:
        return {}

# =============================================
# FINAL PIPELINE
# =============================================
def extract_final(ocr_text):
    cleaned = clean_ocr(ocr_text)

    name = extract_name(ocr_text)
    addr_resp = call_ollama(cleaned)
    addr_data = extract_json(addr_resp)

    return {
        "recipient_name": name,
        "recipient_address": addr_data.get("recipient_address", "")
    }

# =============================================
# TEST INPUTS
# =============================================
raw_texts = [
    "ship to lex2 2.8 lbs united states 2821 carradale dr roseville ca 95661 zoey dong",
    "fedex ground priority 8150 sierra college blvd ste 230 roseville ca syta saephan",
    "ups ground 41 lbs 2821 carradale dr roseville ca 95661 ky dong",
    "priority mail united states 800 north point parkway roseville ca lalarry andersan"
]

# =============================================
# RUN
# =============================================
print("=== FINAL CORRECT NAME + ADDRESS EXTRACTION ===\n")
start = time.time()

for i, text in enumerate(raw_texts, 1):
    result = extract_final(text)
    print(f"RECORD {i}")
    print(json.dumps(result, indent=2))
    print("-" * 60)

print(f"Completed in {time.time() - start:.2f} seconds")
