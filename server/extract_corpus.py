#!/usr/bin/env python3
"""
Extract vocabulary from all 132 IELTS Reading passage PDFs in the corpus ZIP.
Output: reading-corpus.json with structured word entries and source metadata.
"""
import fitz  # PyMuPDF
import zipfile
import re
import json
import os

ZIP_PATH = r"D:\雅思\final\雅思阅读词汇语料库.zip"
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reading-corpus.json")

def parse_passage_pdf(pdf_bytes):
    """Parse a single passage PDF and return {part1, part2, part3} arrays of word entries."""
    import io
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    lines = [l.strip() for l in full_text.strip().split("\n")]

    # Find PART markers
    part_starts = {}
    for i, line in enumerate(lines):
        if "===== PART 1" in line:
            part_starts[1] = i
        elif "===== PART 2" in line:
            part_starts[2] = i
        elif "===== PART 3" in line:
            part_starts[3] = i

    # Build part ranges
    parts = {}
    sorted_keys = sorted(part_starts.keys())
    for idx, k in enumerate(sorted_keys):
        start = part_starts[k] + 1  # skip the header line
        end = part_starts[sorted_keys[idx + 1]] if idx + 1 < len(sorted_keys) else len(lines)
        parts[k] = lines[start:end]

    result = {"part1": [], "part2": [], "part3": []}

    for part_num, part_lines in parts.items():
        key = f"part{part_num}"
        if part_num <= 2:
            # Word entries: "N." on one line, word on next, phonetic+meaning on next
            # Sometimes number and word are on same line: "10. recede"
            entries = parse_word_entries(part_lines)
            result[key] = entries
        else:
            # Phrase entries: "N." phrase, then meaning on next line
            entries = parse_phrase_entries(part_lines)
            result[key] = entries

    return result


def parse_word_entries(lines):
    """Parse Part 1/2 word entries.
    Two layout variants:
      3-line: "1." | word | "/phonetic/ pos. meaning"
      4-line: "1." | word | "/phonetic/" | "pos. meaning"
      Inline: "10. word" | "/phonetic/ pos. meaning"  (number+word on same line)
      Inline+split: "10. word" | "/phonetic/" | "pos. meaning"
    """
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        num_match = re.match(r"^(\d+)\.?\s*$", line)
        num_inline_match = re.match(r"^(\d+)\.\s+(.+)", line)

        word = None
        phonetic = None
        pos_meaning = None

        if num_inline_match:
            # "10. recede" — number and word on same line
            word = num_inline_match.group(2).strip()
            remaining = lines[i + 1:] if i + 1 < len(lines) else []
            consumed, phonetic, pos_meaning = extract_phonetic_and_meaning(remaining)
            i += 1 + consumed
        elif num_match:
            # "1." on its own line, word on next
            if i + 1 < len(lines) and lines[i + 1]:
                word = lines[i + 1].strip()
                remaining = lines[i + 2:] if i + 2 < len(lines) else []
                consumed, phonetic, pos_meaning = extract_phonetic_and_meaning(remaining)
                i += 2 + consumed
            else:
                i += 1
        else:
            i += 1
            continue

        if word:
            entry = build_word_entry(word, phonetic, pos_meaning)
            if entry:
                entries.append(entry)

    return entries


def extract_phonetic_and_meaning(remaining_lines):
    """Given lines after the word, extract phonetic and pos+meaning.
    Handles these layouts:
      A) "/phonetic/ pos. meaning"           (1 line: phonetic + pos+meaning combined)
      B) "/phonetic/" then "pos. meaning"     (2 lines: phonetic, then pos+meaning)
      C) "pos." then "/phonetic/" then "meaning" (3 lines: standalone pos, phonetic, meaning)
      D) "pos. meaning"                        (1 line: no phonetic, just pos+meaning)
    Returns (lines_consumed, phonetic_str, pos_meaning_str)."""
    consumed = 0
    phonetic = None
    pos_meaning = None

    # Skip blanks
    idx = 0
    while idx < len(remaining_lines) and not remaining_lines[idx].strip():
        idx += 1
        consumed += 1

    if idx >= len(remaining_lines):
        return consumed, None, None

    first = remaining_lines[idx].strip()

    # Case C: standalone pos (e.g. "n.", "adj.", "v.", "n./v.") followed by phonetic, then meaning
    is_standalone_pos = re.match(
        r"^(?:adj|n|v|adv|prep|conj|pron|art|num|abbr|modal|aux)\.?(?:/(?:adj|n|v|adv|prep|conj|pron|art|num|abbr|modal|aux)\.?)*$",
        first
    )
    if is_standalone_pos:
        pos_str = first
        consumed += 1
        idx += 1
        # Next non-blank line: phonetic
        while idx < len(remaining_lines) and not remaining_lines[idx].strip():
            idx += 1
            consumed += 1
        if idx < len(remaining_lines):
            ph_line = remaining_lines[idx].strip()
            if ph_line.startswith("/"):
                ph_match = re.match(r"^(/[^/]+/)\s*(.*)", ph_line)
                if ph_match:
                    phonetic = ph_match.group(1)
                    extra = ph_match.group(2).strip()
                    if extra:
                        pos_meaning = pos_str + " " + extra
                        consumed += 1
                        idx += 1
                        return consumed, phonetic, pos_meaning
                # Just phonetic on its own line
                phonetic = ph_line
                consumed += 1
                idx += 1
                # Next non-blank line: meaning
                while idx < len(remaining_lines) and not remaining_lines[idx].strip():
                    idx += 1
                    consumed += 1
                if idx < len(remaining_lines):
                    pos_meaning = pos_str + " " + remaining_lines[idx].strip()
                    consumed += 1
            else:
                # No phonetic, this is the meaning
                pos_meaning = pos_str + " " + ph_line
                consumed += 1
        return consumed, phonetic, pos_meaning

    # Case A/B: first line starts with / (phonetic)
    is_phonetic = first.startswith("/")

    if is_phonetic:
        # Check if the line has BOTH phonetic and pos+meaning (e.g. "/ˈprɪnsəpl/ n. 原则；原理")
        ph_match = re.match(r"^(/[^/]+/)\s*(.+)", first)
        if ph_match and ph_match.group(2).strip():
            # Both on same line
            phonetic = ph_match.group(1)
            pos_meaning = ph_match.group(2).strip()
            consumed += 1
            idx += 1
        else:
            # Just phonetic on its own line; pos+meaning on next line
            phonetic = first
            consumed += 1
            idx += 1
            # Next non-blank line should be pos+meaning
            while idx < len(remaining_lines) and not remaining_lines[idx].strip():
                idx += 1
                consumed += 1
            if idx < len(remaining_lines):
                pos_meaning = remaining_lines[idx].strip()
                consumed += 1
    else:
        # Case D: no phonetic, just pos+meaning on same line
        pos_meaning = first
        consumed += 1

    return consumed, phonetic, pos_meaning


def build_word_entry(word, phonetic, pos_meaning):
    """Build a word entry from word, optional phonetic, and pos+meaning string."""
    pos = ""
    meaning = ""
    phon = phonetic or ""

    if pos_meaning:
        rest = pos_meaning
        # Check if it starts with phonetic (inline format)
        ph_match = re.match(r"^(/[^/]+/)\s*(.*)", rest)
        if ph_match:
            phon = ph_match.group(1)
            rest = ph_match.group(2)

        # Extract part of speech
        pos_match = re.match(
            r"^((?:adj|n|v|adv|prep|conj|pron|art|num|abbr|modal|aux)\.?"
            r"(?:/(?:adj|n|v|adv|prep|conj|pron|art|num|abbr|modal|aux)\.?)*)\s*(.*)",
            rest
        )
        if pos_match:
            pos = pos_match.group(1)
            meaning = pos_match.group(2)
        else:
            meaning = rest

    return {
        "word": word,
        "phonetic": phon,
        "pos": pos,
        "meaning": meaning
    }


def parse_phrase_entries(lines):
    """Parse Part 3 phrase entries. Format: number, phrase, meaning."""
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        num_match = re.match(r"^(\d+)\.?\s*$", line)
        num_inline_match = re.match(r"^(\d+)\.\s+(.+)", line)

        phrase = None
        meaning = None

        if num_inline_match:
            phrase = num_inline_match.group(2).strip()
            if i + 1 < len(lines) and lines[i + 1]:
                meaning = lines[i + 1].strip()
                i += 2
            else:
                i += 1
        elif num_match:
            if i + 1 < len(lines) and lines[i + 1]:
                phrase = lines[i + 1].strip()
                if i + 2 < len(lines) and lines[i + 2]:
                    meaning = lines[i + 2].strip()
                    i += 3
                else:
                    i += 2
            else:
                i += 1
        else:
            i += 1
            continue

        if phrase:
            entries.append({"phrase": phrase, "meaning": meaning or ""})

    return entries


def parse_source_from_path(path):
    """Extract 剑雅号, Test, Passage from path like '雅思阅读词汇语料库/语料库中心（完结）/剑雅10/剑雅10Test1_完结/剑雅10-Test1-Passage1.pdf'"""
    basename = os.path.basename(path)
    # Match: 剑雅10-Test1-Passage1.pdf
    m = re.match(r"剑雅(\d+)-Test(\d+)-Passage(\d+)", basename)
    if m:
        return {
            "cambridge": int(m.group(1)),
            "test": int(m.group(2)),
            "passage": int(m.group(3)),
            "label": f"剑雅{m.group(1)} Test {m.group(2)} Passage {m.group(3)}"
        }
    return {"cambridge": 0, "test": 0, "passage": 0, "label": basename}


def main():
    z = zipfile.ZipFile(ZIP_PATH, "r")
    names = z.namelist()
    passage_pdfs = sorted([n for n in names if n.endswith(".pdf") and "Passage" in n])

    print(f"Processing {len(passage_pdfs)} passage PDFs...")

    corpus = []
    stats = {"total_words": 0, "total_phrases": 0, "by_cambridge": {}}

    for idx, pdf_path in enumerate(passage_pdfs):
        source = parse_source_from_path(pdf_path)
        pdf_bytes = z.read(pdf_path)

        try:
            parsed = parse_passage_pdf(pdf_bytes)
        except Exception as e:
            print(f"  ERROR parsing {pdf_path}: {e}")
            continue

        part1_count = len(parsed["part1"])
        part2_count = len(parsed["part2"])
        part3_count = len(parsed["part3"])

        entry = {
            "id": f"cam{source['cambridge']}-t{source['test']}-p{source['passage']}",
            "source": source,
            "part1": parsed["part1"],
            "part2": parsed["part2"],
            "part3": parsed["part3"],
            "wordCount": part1_count + part2_count,
            "phraseCount": part3_count,
            "totalCount": part1_count + part2_count + part3_count
        }
        corpus.append(entry)

        stats["total_words"] += part1_count + part2_count
        stats["total_phrases"] += part3_count

        cam = source["cambridge"]
        if cam not in stats["by_cambridge"]:
            stats["by_cambridge"][cam] = {"passages": 0, "words": 0, "phrases": 0}
        stats["by_cambridge"][cam]["passages"] += 1
        stats["by_cambridge"][cam]["words"] += part1_count + part2_count
        stats["by_cambridge"][cam]["phrases"] += part3_count

        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(passage_pdfs)}...")

    # Sort by cambridge, test, passage
    corpus.sort(key=lambda x: (x["source"]["cambridge"], x["source"]["test"], x["source"]["passage"]))

    output = {
        "schemaVersion": 1,
        "title": "IELTS Reading Vocabulary Corpus",
        "description": "剑雅10-20阅读词汇语料库，132篇Passage，每篇含生死词/理解提速词/词组搭配三部分",
        "totalPassages": len(corpus),
        "totalWords": stats["total_words"],
        "totalPhrases": stats["total_phrases"],
        "byCambridge": {str(k): v for k, v in sorted(stats["by_cambridge"].items())},
        "passages": corpus
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Output: {OUTPUT_PATH}")
    print(f"Total passages: {len(corpus)}")
    print(f"Total words: {stats['total_words']}")
    print(f"Total phrases: {stats['total_phrases']}")
    print(f"\nBy Cambridge:")
    for cam in sorted(stats["by_cambridge"].keys()):
        s = stats["by_cambridge"][cam]
        print(f"  剑雅{cam}: {s['passages']} passages, {s['words']} words, {s['phrases']} phrases")


if __name__ == "__main__":
    main()
