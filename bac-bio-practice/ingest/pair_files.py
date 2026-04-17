"""
Discovers and pairs test/barem PDF files from the source directory.

Strategy:
1. Classify each PDF as either a test file or a barem file based on filename markers.
2. Normalise each filename into a canonical key by stripping the test/barem markers
   and normalising separators and case.
3. Match test files to barem files by their canonical key.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Markers that identify barem files (checked BEFORE test markers)
_BAREM_MARKERS = [
    "BAREM", "Barem", "barem",
    "Bar", "bar",
]

# Markers that identify test files
_TEST_MARKERS = [
    "subiecte", "subiect",
    "Test", "test",
    "var",
]


def classify_file(filename: str) -> Optional[str]:
    """Return 'test', 'barem', or None."""
    stem = Path(filename).stem
    # Barem markers checked first because some files contain both (e.g. "BAREM-...-bar-...")
    for m in _BAREM_MARKERS:
        # Use word-boundary-ish check: marker preceded/followed by separator or string edge
        pattern = r'(?:^|[-_ .])' + re.escape(m) + r'(?:$|[-_ .])'
        if re.search(pattern, stem):
            return "barem"
    for m in _TEST_MARKERS:
        pattern = r'(?:^|[-_ .])' + re.escape(m) + r'(?:$|[-_ .])'
        if re.search(pattern, stem):
            return "test"
    return None


def _normalise_key(filename: str) -> str:
    """
    Strip test/barem markers from filename and normalise to produce a matching key.

    The idea: after removing all markers that distinguish test from barem,
    what remains should be identical for paired files.
    """
    stem = Path(filename).stem

    # Remove known barem/test markers (case-insensitive, with surrounding separators)
    # Order matters: remove longer markers first
    all_markers = [
        "subiecte", "subiect",
        "BAREM", "Barem", "barem",
        "Test", "test",
        "Bar", "bar",
        "var",
        "PDF",
    ]
    result = stem
    for marker in all_markers:
        # Remove marker surrounded by separators or string boundaries.
        # Use (?<= | ^) and (?= | $) style anchors with [-_ .] as separators
        # since \b doesn't treat _ as a boundary.
        result = re.sub(
            r'(?:(?<=[-_ .])|(?<=^))' + re.escape(marker) + r'(?=[-_ .]|$)',
            '',
            result,
            flags=re.IGNORECASE,
        )

    # Normalise separators: replace any run of [-_. ] with a single dash
    result = re.sub(r'[-_ .]+', '-', result)
    # Strip leading/trailing dashes
    result = result.strip('-')
    # Lowercase for comparison
    result = result.lower()
    return result


def extract_year(filename: str) -> Optional[int]:
    """Try to extract a 4-digit year (2000-2099) from a filename."""
    # Look for standalone 4-digit year
    matches = re.findall(r'(?:^|[^0-9])(20[0-9]{2})(?:$|[^0-9])', filename)
    if matches:
        # Return the first plausible year
        return int(matches[0])
    return None


def discover_pairs(source_dir: str) -> List[Dict]:
    """
    Scan source_dir for PDF files, classify and pair them.

    Returns a list of dicts:
      {
        'test_file': str (full path),
        'barem_file': str (full path),
        'year': int or None,
        'test_id': str (canonical key used as DB id),
      }
    Also returns unpaired files separately.
    """
    source = Path(source_dir)
    if not source.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    pdfs = sorted(f for f in os.listdir(source) if f.lower().endswith('.pdf'))

    test_files: Dict[str, str] = {}   # key -> filename
    barem_files: Dict[str, str] = {}  # key -> filename
    unclassified: List[str] = []

    for pdf in pdfs:
        kind = classify_file(pdf)
        key = _normalise_key(pdf)
        if kind == "test":
            test_files[key] = pdf
        elif kind == "barem":
            barem_files[key] = pdf
        else:
            unclassified.append(pdf)

    # Match by key
    paired = []
    unpaired_tests = []
    unpaired_barems = []
    matched_barem_keys = set()

    for key, test_fn in sorted(test_files.items()):
        if key in barem_files:
            barem_fn = barem_files[key]
            matched_barem_keys.add(key)
            year = extract_year(test_fn) or extract_year(barem_fn)
            paired.append({
                'test_file': str(source / test_fn),
                'barem_file': str(source / barem_fn),
                'year': year,
                'test_id': key,
            })
        else:
            unpaired_tests.append((key, test_fn))

    for key, barem_fn in sorted(barem_files.items()):
        if key not in matched_barem_keys:
            unpaired_barems.append((key, barem_fn))

    # Second pass: fuzzy matching for remaining unpaired files.
    # Try matching where one key is a prefix of the other, or keys match after
    # stripping trailing -1 suffixes or lro markers.
    still_unpaired_tests = []
    still_unpaired_barems_keys = {k: fn for k, fn in unpaired_barems}

    for tkey, test_fn in unpaired_tests:
        best_match = None
        # Try: strip trailing "-1" segments from test key
        tkey_stripped = re.sub(r'(-\d+)+$', '', tkey)
        for bkey in list(still_unpaired_barems_keys.keys()):
            bkey_stripped = re.sub(r'(-\d+)+$', '', bkey)
            # Also try without lro
            tkey_nolro = re.sub(r'-lro$', '', tkey_stripped)
            bkey_nolro = re.sub(r'-lro$', '', bkey_stripped)
            if (tkey_stripped == bkey_stripped
                    or tkey_stripped == bkey
                    or tkey == bkey_stripped
                    or tkey_nolro == bkey_nolro):
                best_match = bkey
                break
        if best_match:
            barem_fn = still_unpaired_barems_keys.pop(best_match)
            matched_barem_keys.add(best_match)
            year = extract_year(test_fn) or extract_year(barem_fn)
            paired.append({
                'test_file': str(source / test_fn),
                'barem_file': str(source / barem_fn),
                'year': year,
                'test_id': tkey,
            })
        else:
            still_unpaired_tests.append(test_fn)

    unpaired_tests_final = still_unpaired_tests
    unpaired_barems_final = list(still_unpaired_barems_keys.values())

    if unpaired_tests_final or unpaired_barems_final or unclassified:
        import sys
        if unpaired_tests_final:
            print(f"[pair] WARNING: {len(unpaired_tests_final)} test file(s) without barem:", file=sys.stderr)
            for f in unpaired_tests_final:
                print(f"  - {f}", file=sys.stderr)
        if unpaired_barems_final:
            print(f"[pair] WARNING: {len(unpaired_barems_final)} barem file(s) without test:", file=sys.stderr)
            for f in unpaired_barems_final:
                print(f"  - {f}", file=sys.stderr)
        if unclassified:
            print(f"[pair] WARNING: {len(unclassified)} unclassified file(s):", file=sys.stderr)
            for f in unclassified:
                print(f"  - {f}", file=sys.stderr)

    return paired


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../Test_Bio_cu_bareme"
    pairs = discover_pairs(src)
    print(f"Found {len(pairs)} test/barem pairs.")
    for p in pairs[:5]:
        print(f"  {p['test_id']}  year={p['year']}")
        print(f"    test:  {os.path.basename(p['test_file'])}")
        print(f"    barem: {os.path.basename(p['barem_file'])}")
