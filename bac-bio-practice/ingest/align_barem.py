"""
Aligns segmented questions with their barem (answer key) entries.

Matching strategy:
  - For most questions: match by (subject, part_label, number) triple.
  - For Subject I-C and I-D: the barem gives all answers in one block,
    so we parse them into per-item answers.
"""

import re
from typing import Dict, List, Optional, Tuple


def _parse_mc_answers(barem_text: str) -> Dict[str, str]:
    """
    Parse MC answers from barem I-C.
    Expected format like: "1b; 2d; 3d; 4d; 5c" or "1.b; 2.d; ..."
    """
    answers = {}
    # Match patterns: 1b, 1.b, 1-b, 1 b
    for m in re.finditer(r'(\d+)\s*[.\-]?\s*([a-d])', barem_text, re.IGNORECASE):
        num = m.group(1)
        letter = m.group(2).lower()
        answers[num] = letter
    return answers


def _parse_tf_answers(barem_text: str) -> Dict[str, str]:
    """
    Parse true/false answers from barem I-D.
    Expected format: "1F; 2A; 3F" + corrections for false ones.
    """
    answers = {}
    # Match patterns: 1F, 1.F, 1A, etc.
    for m in re.finditer(r'(\d+)\s*[.\-]?\s*([AF])', barem_text):
        num = m.group(1)
        verdict = m.group(2).upper()
        answers[num] = verdict

    # The full text contains the corrections too, so we store the whole thing
    # keyed by item number
    return answers


def align(questions: List[Dict], barem_entries: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Align questions with barem answers.

    Returns:
      - aligned: list of question dicts augmented with 'barem_answer' and 'barem_notes'
      - unaligned: list of question dicts that couldn't be matched
    """
    # Build lookup from barem entries
    barem_by_key: Dict[Tuple, str] = {}
    mc_answers: Dict[str, str] = {}
    tf_answers: Dict[str, str] = {}
    full_barem_ic = ""
    full_barem_id = ""

    for entry in barem_entries:
        subj = entry['subject'].upper()
        part = (entry.get('part_label') or '').upper()
        num = entry.get('number', '1').lower()

        if subj == 'I' and part == 'C' and num == 'all':
            mc_answers = _parse_mc_answers(entry['answer'])
            full_barem_ic = entry['answer']
        elif subj == 'I' and part == 'D' and num == 'all':
            tf_answers = _parse_tf_answers(entry['answer'])
            full_barem_id = entry['answer']
        else:
            key = (subj, part, num)
            barem_by_key[key] = entry['answer']

    aligned = []
    unaligned = []

    for q in questions:
        subj = q['subject'].upper()
        part = (q.get('part_label') or '').upper()
        num = q.get('number', '1').lower()

        barem_answer = None
        barem_notes = None

        if subj == 'I' and part == 'C':
            # Look up individual MC answer
            if num in mc_answers:
                barem_answer = mc_answers[num]
                barem_notes = full_barem_ic
            else:
                barem_answer = full_barem_ic  # fallback: give whole block

        elif subj == 'I' and part == 'D':
            # Look up individual TF answer
            if num in tf_answers:
                barem_answer = tf_answers[num]
                barem_notes = full_barem_id
            else:
                barem_answer = full_barem_id

        else:
            key = (subj, part, num)
            if key in barem_by_key:
                barem_answer = barem_by_key[key]
            else:
                # Try fallback: match just (subject, part) with number='1'
                fallback_key = (subj, part, '1')
                if fallback_key in barem_by_key:
                    barem_answer = barem_by_key[fallback_key]
                    barem_notes = "Fallback: matched entire part"

        q_out = dict(q)
        if barem_answer is not None:
            q_out['barem_answer'] = barem_answer
            q_out['barem_notes'] = barem_notes
            aligned.append(q_out)
        else:
            q_out['barem_answer'] = ''
            q_out['barem_notes'] = 'UNALIGNED'
            unaligned.append(q_out)

    return aligned, unaligned
