import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

# -----------------------------
# MODEL
# -----------------------------
model_id = "openai/privacy-filter"

tokenizer = AutoTokenizer.from_pretrained(model_id)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForTokenClassification.from_pretrained(model_id).to(device)

id2label = model.config.id2label


# -----------------------------
# FALLBACK PATTERNS (CRITICAL FIX)
# -----------------------------
FALLBACK_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "PHONE": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
}


# -----------------------------
# MAIN REDACTION FUNCTION
# -----------------------------
def redact(text: str):

    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits[0]
    preds = torch.argmax(logits, dim=-1)

    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    labels = [id2label[p.item()] for p in preds]

    # -----------------------------
    # DEBUG (optional)
    # -----------------------------
    print("\n--- DEBUG ---")
    print("TOKENS:", tokens)
    print("LABELS:", labels)
    print("-------------\n")

    # -----------------------------
    # BIO ENTITY PARSING (FIXED)
    # -----------------------------
    entities = []
    current_tokens = []
    current_label = None

    for token, label in zip(tokens, labels):

        if token in ["[CLS]", "[SEP]"]:
            continue

        # clean subword tokens
        clean_token = token.replace("Ġ", "").replace("##", "")

        # NO ENTITY
        if label == "O":
            if current_tokens:
                entities.append((current_label, current_tokens))
                current_tokens = []
                current_label = None
            continue

        # START ENTITY
        if label.startswith("B-"):

            if current_tokens:
                entities.append((current_label, current_tokens))

            current_label = label.replace("B-", "")
            current_tokens = [clean_token]
            continue

        # INSIDE ENTITY
        if label.startswith("I-") or label.startswith("E-"):
            current_tokens.append(clean_token)
            continue

    # flush last
    if current_tokens:
        entities.append((current_label, current_tokens))

    # -----------------------------
    # FALLBACK (CRITICAL FIX)
    # -----------------------------
    fallback_entities = []

    for label, pattern in FALLBACK_PATTERNS.items():

        for match in re.findall(pattern, text):

            fallback_entities.append((label, [match]))

    # merge model + fallback
    entities.extend(fallback_entities)

    # -----------------------------
    # BUILD OUTPUT
    # -----------------------------
    output_text = text
    structured_entities = []

    # stable confidence proxy (model-level, not token noise)
    confidence = float(torch.softmax(logits, dim=-1).max().item())

    for label, tokens_list in entities:

        value = "".join(tokens_list).replace(" ", "")

        structured_entities.append({
            "type": label,
            "value": value,
            "confidence": round(confidence, 2)
        })

        # redact in text
        output_text = output_text.replace(value, f"[{label}]")

    return {
        "text": output_text,
        "entities": structured_entities
    }