import os
from . import truetypealgorithm as tta

def get_all_filenames_in_folder(folder_path):
    filenames = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            filenames.append(filename) 
    return filenames

def total_score(total_result, user_file):
    user_basename = os.path.basename(user_file)
    all_exact_matches = set()
    all_partial_matches = set()
    all_matched_pairs = []

    for result in total_result:
        all_exact_matches.update(result.get("exact_matches", []))
        all_partial_matches.update(result.get("partial_matches", []))
        all_matched_pairs.extend(result.get("matched_pairs", []))

    all_partial_matches -= all_exact_matches

    user_sentences = tta.read_file(user_file)
    total_count = len(user_sentences)

    if total_count == 0:
        return {
            "total_exact_score": 0.0,
            "total_partial_score": 0.0,
            "unique_score": 100.0,
            "user_files": [],
            "exact_matches": [],
            "partial_matches": [],
            "plagiarism_files": [],
            "submittedDocument": "",
            "plagiarisedSnippets": [],
            "matched_pairs": []
        }

    exact_count = len(all_exact_matches)
    partial_count = len(all_partial_matches)
    unique_count = total_count - exact_count - partial_count

    total_exact_score = (exact_count / total_count) * 100
    total_partial_score = (partial_count / total_count) * 100
    unique_score = (unique_count / total_count) * 100

    files_with_matches = []
    for result in total_result:
        if result.get("exact_score", 0) > 0 or result.get("partial_score", 0) > 0:
            files_with_matches.append(result.get("filename"))

    citation_statuses = [pair.get("citation_status", "uncited") for pair in all_matched_pairs]
    # If no citations found, assume not properly cited
    if not citation_statuses:
        document_citation_status = "No citations found"
    elif all(status == "proper" for status in citation_statuses):
        document_citation_status = "Properly cited"
    else:
        document_citation_status = "Not properly cited"

    # Collect unique citation texts from matched pairs that have proper citations
    citations = []
    for pair in all_matched_pairs:
        if pair.get("citation_status") == "proper":
            citation_text = pair.get("citation_text")  
            if citation_text and citation_text not in citations:
                citations.append(citation_text)

    return {
        "uploaded_filename": user_basename, 
        "total_exact_score": total_exact_score,
        "total_partial_score": total_partial_score,
        "unique_score": unique_score,
        "user_files": list(user_sentences),
        "exact_matches": list(all_exact_matches),
        "partial_matches": list(all_partial_matches),
        "plagiarism_files": files_with_matches,
        "submittedDocument": "\n".join(user_sentences),
        "plagiarisedSnippets": list(all_exact_matches.union(all_partial_matches)),
        "matched_pairs": all_matched_pairs,
        "document_citation_status": document_citation_status,
        "citations_found": citations,
    }


if __name__ == "__main__":
    folder = "initial_doc"
    files = get_all_filenames_in_folder(folder)

    user_file = os.path.join(folder, "Proposal.docx")
    total_result = []

    for file in files:
        file_path = os.path.join(folder, file)
        if file_path == user_file:
            continue
        print(f"Comparing with file: {file_path}")
        try:
            result = tta.get_plagiarism_report(user_file, file_path)
            total_result.append(result)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    final_plag = total_score(total_result, user_file)
    print(final_plag)
