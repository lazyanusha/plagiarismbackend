# citation_checker.py
import re
import psycopg2

from app.database.db_connect import test_database_connection


def extract_references_section(lines):
    for i, line in enumerate(lines):
        if re.search(r'^(references|bibliography)\s*$', line.strip(), re.IGNORECASE):
            return lines[i + 1:]
    return []


def normalize_reference_entries(ref_lines):
    ref_keys = set()
    ieee_map = {}

    for i, line in enumerate(ref_lines):
        match = re.match(r'\[(\d+)\]\s*(.*)', line)
        if match:
            ref_num = match.group(1)
            rest = match.group(2)
            ieee_map[ref_num] = rest

        match = re.search(r'(\b[A-Z][a-zA-Z]+)[^\n]*?(\d{4})', line)
        if match:
            author = match.group(1).lower()
            year = match.group(2)
            ref_keys.add(f"{author}_{year}")

        match = re.search(r'(\b[A-Z][a-zA-Z]+),\s+[A-Z][a-zA-Z]+.*?(\d{4})', line)
        if match:
            author = match.group(1).lower()
            year = match.group(2)
            ref_keys.add(f"{author}_{year}")

    return ref_keys, ieee_map


def fetch_db_references():
    conn =test_database_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.name, r.publication_date
        FROM authors a
        JOIN resource_authors ra ON a.id = ra.author_id
        JOIN resources r ON r.id = ra.resource_id
    """)
    rows = cursor.fetchall()
    db_keys = set()
    for name, pub_date in rows:
        if pub_date:
            db_keys.add(f"{name.lower().split()[0]}_{pub_date.year}")
        else:
            db_keys.add(f"{name.lower().split()[0]}_unknown")

    cursor.close()
    conn.close()
    return db_keys


def find_in_text_citations(sentence):
    keys = []
    ieee_numbers = []
    citation_texts = []

    for match in re.finditer(r'\(([A-Z][a-zA-Z]+),\s*(\d{4})\)', sentence):
        author, year = match.groups()
        keys.append(f"{author.lower()}_{year}")
        citation_texts.append(match.group(0))

    for match in re.finditer(r'\(([A-Z][a-zA-Z]+)\s+\d+\)', sentence):
        author = match.group(1)
        keys.append(f"{author.lower()}_unknown")
        citation_texts.append(match.group(0))

    for match in re.finditer(r'\[(\d+(?:[-,]\d+)*)\]', sentence):
        citation = match.group(0)
        parts = re.split(r'[-,]', match.group(1))
        ieee_numbers.extend(parts)
        citation_texts.append(citation)

    return keys, ieee_numbers, citation_texts


def classify_citation_status(matched_pairs, doc1_sentences, doc2_sentences, doc2_lines):
    ref_lines = extract_references_section(doc2_lines)
    ref_keys, ieee_map = normalize_reference_entries(ref_lines)
    db_keys = fetch_db_references()
    ref_keys.update(db_keys)

    for pair in matched_pairs:
        idx = pair['doc1_idx']
        context_indices = range(max(0, idx - 2), min(len(doc2_sentences), idx + 3))
        context = [doc2_sentences[i] for i in context_indices]

        found_keys = set()
        found_ieee = set()
        citation_texts = []

        for sent in context:
            keys, ieee_nums, ctexts = find_in_text_citations(sent)
            found_keys.update(keys)
            found_ieee.update(ieee_nums)
            citation_texts.extend(ctexts)

        status = "uncited"

        ieee_matched = any(num in ieee_map for num in found_ieee)
        key_matched = any(key in ref_keys for key in found_keys)

        if ieee_matched or key_matched:
            status = "properly_cited"
        elif found_keys or found_ieee:
            status = "mismatched"

        pair['citation_status'] = status
        pair['citation_text'] = ", ".join(set(citation_texts))

    return matched_pairs


def split_text_and_references(full_text):
    lines = [line.strip() for line in full_text.strip().split('\n') if line.strip()]
    ref_start_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r'^(references|bibliography)\s*$', lines[i], re.IGNORECASE):
            ref_start_idx = i
            break

    if ref_start_idx is not None:
        main_lines = lines[:ref_start_idx]
        references_lines = lines[ref_start_idx + 1:]
    else:
        main_lines = lines
        references_lines = []

    return main_lines, references_lines