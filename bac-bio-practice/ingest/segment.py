"""
Segments extracted test/barem text into Subiectul I/II/III and individual questions.

The structure is highly regular:
  SUBIECTUL I      -> parts A, B, C, D
  SUBIECTUL al II-lea  -> parts A, B
  SUBIECTUL al III-lea -> items 1, 2
"""

import re
from typing import Dict, List, Optional, Tuple


# ---------- Subject-level splitting ----------

# Matches "SUBIECTUL I", "SUBIECTUL al II-lea", "SUBIECTUL al III-lea"
# Also handles "SUBIECTUL al II -lea" (space before -lea)
_SUBJ_RE = re.compile(
    r'SUBIECTUL\s+'
    r'(?:'
    r'I(?:\s|$|\()'               # SUBIECTUL I (30 ...
    r'|al\s+II\s*-?\s*lea'        # SUBIECTUL al II-lea
    r'|al\s+III\s*-?\s*lea'       # SUBIECTUL al III-lea
    r')',
    re.IGNORECASE,
)

_SUBJ_NUM_RE = re.compile(
    r'SUBIECTUL\s+'
    r'(?:'
    r'(I)(?:\s|$|\()'
    r'|al\s+(II)\s*-?\s*lea'
    r'|al\s+(III)\s*-?\s*lea'
    r')',
    re.IGNORECASE,
)


def _identify_subject(text: str) -> Optional[str]:
    """Return 'I', 'II', or 'III' from a subject header line."""
    m = _SUBJ_NUM_RE.search(text)
    if not m:
        return None
    return m.group(1) or m.group(2) or m.group(3)


def split_subjects(text: str) -> Dict[str, str]:
    """
    Split full text into subject sections.
    Returns {'I': '...', 'II': '...', 'III': '...'}.
    """
    # Find all subject header positions
    matches = list(_SUBJ_NUM_RE.finditer(text))
    if not matches:
        return {}

    subjects = {}
    for i, m in enumerate(matches):
        subj = m.group(1) or m.group(2) or m.group(3)
        subj = subj.upper()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        subjects[subj] = text[start:end].strip()

    return subjects


# ---------- Part-level splitting within subjects ----------

# Part headers: "A 4 puncte", "A. 4 puncte", "B 6 puncte", etc.
_PART_LABEL_RE = re.compile(
    r'^([A-D])\.?\s+\d+\s*(?:de\s+)?punct',
    re.IGNORECASE | re.MULTILINE,
)

# For Subiectul III: "1. 14 puncte", "2. 16 puncte"
_ITEM_NUM_RE = re.compile(
    r'^(\d+)\.\s+\d+\s*(?:de\s+)?punct',
    re.IGNORECASE | re.MULTILINE,
)


def split_parts(subject_text: str, subject_num: str) -> Dict[str, str]:
    """
    Split a subject section into its parts.

    For Subiectul I: returns {'A': '...', 'B': '...', 'C': '...', 'D': '...'}
    For Subiectul II: returns {'A': '...', 'B': '...'}
    For Subiectul III: returns {'1': '...', '2': '...'}
    """
    if subject_num in ('I', 'II'):
        return _split_by_pattern(subject_text, _PART_LABEL_RE)
    else:  # III
        return _split_by_pattern(subject_text, _ITEM_NUM_RE)


def _split_by_pattern(text: str, pattern: re.Pattern) -> Dict[str, str]:
    matches = list(pattern.finditer(text))
    if not matches:
        return {}

    parts = {}
    for i, m in enumerate(matches):
        label = m.group(1).upper()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        parts[label] = text[start:end].strip()

    return parts


# ---------- Sub-question splitting within parts ----------

# Sub-questions: a), b), c), d) — or a., b., c., d. at line start
_SUB_Q_RE = re.compile(
    r'^([a-d])\s*[).\u2013\u2014-]',
    re.IGNORECASE | re.MULTILINE,
)

# For Subject I-C: numbered multiple choice items  "1. text" or "1.text"
_MC_ITEM_RE = re.compile(
    r'^(\d+)\.\s+',
    re.MULTILINE,
)


def split_mc_items(part_text: str) -> Dict[str, str]:
    """Split Subject I-C into individual multiple-choice questions (1-5)."""
    # First, find the instruction line and skip it
    # The MC items start with "1. ..."
    matches = list(_MC_ITEM_RE.finditer(part_text))
    if not matches:
        return {}

    items = {}
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(part_text)
        items[num] = part_text[start:end].strip()

    return items


def split_tf_items(part_text: str) -> Dict[str, str]:
    """Split Subject I-D into individual true/false statements (1-3)."""
    # Same numbered pattern
    matches = list(_MC_ITEM_RE.finditer(part_text))
    if not matches:
        return {}

    items = {}
    for i, m in enumerate(matches):
        num = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(part_text)
        items[num] = part_text[start:end].strip()

    return items


def split_sub_questions(part_text: str) -> Dict[str, str]:
    """Split a part into sub-questions (a, b, c, d)."""
    matches = list(_SUB_Q_RE.finditer(part_text))
    if not matches:
        return {}

    subs = {}
    for i, m in enumerate(matches):
        label = m.group(1).lower()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(part_text)
        subs[label] = part_text[start:end].strip()

    return subs


# ---------- Extract points from part header ----------

_POINTS_RE = re.compile(r'(\d+)\s*(?:de\s+)?punct', re.IGNORECASE)


def extract_points(text: str) -> int:
    """Extract the point value from the first line of a part."""
    first_line = text.split('\n')[0]
    m = _POINTS_RE.search(first_line)
    return int(m.group(1)) if m else 0


# Strips "A 4 puncte " / "B. 6 de puncte " prefix from prompt text
_PROMPT_PREFIX_RE = re.compile(
    r'^[A-D]\.?\s+\d+\s*(?:de\s+)?puncte?\s+',
    re.IGNORECASE,
)


def strip_part_header(text: str) -> str:
    """Remove the part header (e.g. 'A 4 puncte ') from the beginning of prompt text."""
    return _PROMPT_PREFIX_RE.sub('', text)


# ---------- High-level segmentation ----------

def segment_test(text: str) -> List[Dict]:
    """
    Segment full test text into a list of question dicts.

    Each dict has:
      - subject: 'I', 'II', or 'III'
      - part_label: 'A', 'B', 'C', 'D' or '1', '2'
      - number: question number within part (e.g. '1', '2', ... or 'a', 'b', ...)
      - prompt: the question text
      - points: point value
      - context: any shared context/intro text for the part
    """
    subjects = split_subjects(text)
    questions = []

    for subj_num, subj_text in subjects.items():
        parts = split_parts(subj_text, subj_num)

        if not parts:
            # Fallback: treat entire subject as one question
            questions.append({
                'subject': subj_num,
                'part_label': None,
                'number': '1',
                'prompt': subj_text,
                'points': extract_points(subj_text),
                'context': None,
            })
            continue

        for part_label, part_text in parts.items():
            points = extract_points(part_text)

            if subj_num == 'I' and part_label == 'C':
                # Multiple choice: split into 5 items
                mc_items = split_mc_items(part_text)
                # Extract instruction/context (text before first numbered item)
                context = _extract_context_before_items(part_text, _MC_ITEM_RE)
                if mc_items:
                    for num, item_text in mc_items.items():
                        questions.append({
                            'subject': subj_num,
                            'part_label': part_label,
                            'number': num,
                            'prompt': item_text,
                            'points': 2,  # each MC is 2 points
                            'context': context,
                        })
                else:
                    questions.append({
                        'subject': subj_num,
                        'part_label': part_label,
                        'number': '1',
                        'prompt': part_text,
                        'points': points,
                        'context': None,
                    })

            elif subj_num == 'I' and part_label == 'D':
                # True/false: split into 3 items
                tf_items = split_tf_items(part_text)
                context = _extract_context_before_items(part_text, _MC_ITEM_RE)
                if tf_items:
                    for num, item_text in tf_items.items():
                        questions.append({
                            'subject': subj_num,
                            'part_label': part_label,
                            'number': num,
                            'prompt': item_text,
                            'points': 2 if num in ('1', '2', '3') else 0,
                            'context': context,
                        })
                else:
                    questions.append({
                        'subject': subj_num,
                        'part_label': part_label,
                        'number': '1',
                        'prompt': part_text,
                        'points': points,
                        'context': None,
                    })

            elif subj_num == 'I' and part_label in ('A', 'B'):
                # Single question per part
                questions.append({
                    'subject': subj_num,
                    'part_label': part_label,
                    'number': '1',
                    'prompt': strip_part_header(part_text),
                    'points': points,
                    'context': None,
                })

            elif subj_num == 'II':
                # Parts A and B have sub-questions a, b, c, (d)
                subs = split_sub_questions(part_text)
                context = _extract_context_before_items(part_text, _SUB_Q_RE)
                if subs:
                    for sub_label, sub_text in subs.items():
                        questions.append({
                            'subject': subj_num,
                            'part_label': part_label,
                            'number': sub_label,
                            'prompt': sub_text,
                            'points': 0,  # points distributed within barem
                            'context': context,
                        })
                else:
                    questions.append({
                        'subject': subj_num,
                        'part_label': part_label,
                        'number': '1',
                        'prompt': part_text,
                        'points': points,
                        'context': None,
                    })

            elif subj_num == 'III':
                # Items 1 and 2, each with sub-questions a, b, c
                subs = split_sub_questions(part_text)
                context = _extract_context_before_items(part_text, _SUB_Q_RE)
                if subs:
                    for sub_label, sub_text in subs.items():
                        questions.append({
                            'subject': subj_num,
                            'part_label': part_label,
                            'number': sub_label,
                            'prompt': sub_text,
                            'points': 0,
                            'context': context,
                        })
                else:
                    questions.append({
                        'subject': subj_num,
                        'part_label': part_label,
                        'number': '1',
                        'prompt': part_text,
                        'points': points,
                        'context': None,
                    })

    return questions


def _extract_context_before_items(text: str, pattern: re.Pattern) -> Optional[str]:
    """Extract text before the first match of pattern (the intro/context)."""
    m = pattern.search(text)
    if m and m.start() > 0:
        # Get text from after the header line to before the first item
        header_end = text.find('\n')
        if header_end < m.start():
            ctx = text[header_end:m.start()].strip()
            return ctx if ctx else None
    return None


# ---------- Barem segmentation ----------

def segment_barem(text: str) -> List[Dict]:
    """
    Segment barem text into answer entries.

    Returns list of dicts:
      - subject: 'I', 'II', 'III'
      - part_label: 'A', 'B', 'C', 'D' or '1', '2'
      - number: '1', '2', ... or 'a', 'b', ...
      - answer: the barem answer text
    """
    subjects = split_subjects(text)
    answers = []

    for subj_num, subj_text in subjects.items():
        parts = split_parts(subj_text, subj_num)

        if not parts:
            answers.append({
                'subject': subj_num,
                'part_label': None,
                'number': '1',
                'answer': subj_text,
            })
            continue

        for part_label, part_text in parts.items():
            if subj_num == 'I' and part_label == 'C':
                # C answers are typically on one/few lines: "1b; 2d; 3d; 4d; 5c"
                answers.append({
                    'subject': subj_num,
                    'part_label': part_label,
                    'number': 'all',
                    'answer': part_text,
                })

            elif subj_num == 'I' and part_label == 'D':
                # D answers: "1F; 2A; 3F" + corrections
                answers.append({
                    'subject': subj_num,
                    'part_label': part_label,
                    'number': 'all',
                    'answer': part_text,
                })

            elif subj_num == 'I' and part_label in ('A', 'B'):
                answers.append({
                    'subject': subj_num,
                    'part_label': part_label,
                    'number': '1',
                    'answer': part_text,
                })

            elif subj_num in ('II', 'III'):
                # Try to split by sub-questions
                subs = split_sub_questions(part_text)
                if subs:
                    # Also store the full part for fallback
                    for sub_label, sub_text in subs.items():
                        answers.append({
                            'subject': subj_num,
                            'part_label': part_label,
                            'number': sub_label,
                            'answer': sub_text,
                        })
                else:
                    answers.append({
                        'subject': subj_num,
                        'part_label': part_label,
                        'number': '1',
                        'answer': part_text,
                    })

    return answers
