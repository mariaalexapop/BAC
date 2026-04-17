"""
Classifies question types and topics based on subject, part, and content patterns.

Classification rules for question_type:
  I-A  -> fill_blank  (fill in the blanks)
  I-B  -> short_answer (name/associate)
  I-C  -> short_answer (multiple choice - stored as short_answer since user picks a/b/c/d)
  I-D  -> true_false   (true/false with correction)
  II-A -> multi_part   (structured problem with sub-parts)
  II-B -> multi_part   (structured problem with sub-parts)
  III-1 -> multi_part  (structured with sub-parts)
  III-2 -> essay       (includes mini-essay component)
         or multi_part if sub-part doesn't mention "minieseu"

Topic classification uses keyword matching on Romanian biology terms.
"""

import re
from typing import Dict, Optional


VALID_TOPICS = [
    'sistem_nervos', 'analizatori', 'sistem_endocrin', 'sistem_osos',
    'sistem_muscular', 'sistem_digestiv', 'sistem_circulator',
    'sistem_respirator', 'sistem_excretor', 'sistem_reproducator',
    'genetica', 'ecologie_umana', 'alcatuirea_corpului', 'mixt', 'altele',
]

# Keyword rules for topic classification.
# Order matters: more specific patterns first to avoid false matches.
# Each entry: (topic, list_of_keyword_patterns)
TOPIC_RULES = [
    ('analizatori', [
        r'\banalizator', r'\bfotoreceptor', r'\bfonosensibil', r'\bfotosensibil',
        r'\bretină', r'\bretina\b', r'\bcristalin', r'\bcornee',
        r'\bcohlé', r'\bcohle', r'\bmelc\b', r'\btimpan', r'\burechea?\b',
        r'\bochi\b', r'\bochiul', r'\bvedere', r'\bvizual', r'\bauditiv',
        r'\bauz\b', r'\bpata galbenă', r'\bpata oarbă',
        r'\bconuri\b', r'\bbastonaş', r'\bbastonas',
        r'\bgustativ', r'\bolfactiv', r'\btactil',
        r'\bsenzaţi[ei]', r'\bsenzati[ei]',
    ]),
    ('sistem_nervos', [
        r'\bneuron', r'\bsinaps[ăa]', r'\bsinapsa\b', r'\breflex\b',
        r'\barc reflex', r'\bencefal', r'\bcerebel', r'\bbulb rahidian',
        r'\bmăduva?\s+spinăr', r'\bmaduva?\s+spinar',
        r'\bsistemul?\s+nervos', r'\bnerv\b', r'\bnervi\b', r'\bnervos',
        r'\bcerebral', r'\bcortex', r'\bemisfer', r'\baxon', r'\bdendrit',
        r'\bimpuls\s+nervos', r'\bsimpatic', r'\bparasimpatic',
        r'\bvegetativ', r'\bsomatic\b', r'\bganglion',
        r'\bmeninx', r'\bmeninge', r'\blichid\s+cefalorahidian',
        r'\bsubstanţ[ăa]\s+(alb|cenuşi|cenusi)',
    ]),
    ('sistem_endocrin', [
        r'\bhormon', r'\bhipofiz', r'\btiroida?\b', r'\btiroid[ăa]',
        r'\bsuprarena', r'\bpancreas', r'\binsulina?\b', r'\bglucagon',
        r'\badrenalin', r'\btiroxin', r'\bendocrin', r'\bglande?\s+endocrin',
        r'\bepifiz', r'\btimus\b', r'\bsomatotrop', r'\badenohipofiz',
        r'\bneurohipofiz', r'\bestrogen', r'\btestosteron', r'\bprogesteron',
        r'\bcorticoid', r'\bcortizol',
    ]),
    ('sistem_osos', [
        r'\bos\b', r'\boase\b', r'\bosul\b', r'\bschelet', r'\bfemur',
        r'\btibi[ae]\b', r'\bhumerus', r'\bradius\b', r'\bvertebr',
        r'\bcrani[ul]', r'\bcoloana?\s+vertebral', r'\barticulaţi',
        r'\bperiost', r'\bosteon', r'\bosteoporoz', r'\bluxaţi', r'\bfractur',
        r'\bomoplat', r'\bstern\b', r'\bcoast[eă]', r'\bcarpian',
        r'\bscapular[ăa]', r'\bpelvian',
        r'\bentors[ăa]', r'\bentorsa?\b',
        r'\bsistemul?\s+osos',
    ]),
    ('sistem_muscular', [
        r'\bmuşchi', r'\bmuschi', r'\bmuscular', r'\bmiofibrile', r'\bmiozin',
        r'\bactin[ăa]', r'\bcontracţi', r'\bcontracti',
        r'\bbiceps', r'\btriceps', r'\btonusul?\s+muscular',
        r'\batrofie\s+muscular', r'\bdistrofie', r'\btendon',
        r'\bsistemul?\s+muscular', r'\bfibre?\s+muscular',
    ]),
    ('sistem_digestiv', [
        r'\bdigestiv', r'\bdigestie', r'\bstomac', r'\bficat', r'\bintestin',
        r'\besofag', r'\bfaringe', r'\bbil[ăa]\b', r'\bpancrea[st]',
        r'\benzim[ăe]?\s+digestiv', r'\bpepsina?\b', r'\btripsina?\b',
        r'\babsorbţi', r'\babsorti', r'\bdeglutiti', r'\bperistalt',
        r'\bsuc\s+gastric', r'\bsuc\s+pancreatic', r'\bvilozitat',
        r'\bduoden', r'\bjejun', r'\bileon', r'\bcolon', r'\brect\b',
        r'\bsaliv', r'\bglande?\s+salivare',
        r'\bglande?\s+digestive', r'\baparat\s+digestiv',
        r'\bsuc\s+digestiv', r'\baliment',
    ]),
    ('sistem_circulator', [
        r'\bsânge', r'\bsange', r'\binimă', r'\binima\b', r'\bcirculator',
        r'\barteră', r'\bartera\b', r'\barter[ei]', r'\bvenă', r'\bvena\b',
        r'\bvene\b', r'\bcapilar', r'\baortă', r'\baorta\b',
        r'\bhemoglobin', r'\beritrocit', r'\bleucocit', r'\btrombocit',
        r'\bhemati[ei]', r'\bplasm[ăa]\s+sanguin',
        r'\btransfuz', r'\bgrup[ăa]\s+sanguin', r'\baglutinin',
        r'\baglutinogen', r'\brh\b', r'\bsistol', r'\bdiastol',
        r'\bventricul', r'\batriu', r'\bvalvul',
        r'\bciclu\s+cardiac', r'\btensiune\s+arterial',
        r'\bfrecvenţ[ăa]\s+cardiac',
    ]),
    ('sistem_respirator', [
        r'\brespira', r'\bplămân', r'\bplaman', r'\bpulmonar',
        r'\binspirat', r'\bexpirat', r'\bventilat',
        r'\balveol', r'\bbronhi', r'\btrahee', r'\blaringe',
        r'\bdiafragm', r'\bcapacitat[ea]\s+vital', r'\bvolum\s+rezidual',
        r'\bvolum\s+curent', r'\bgaze?\s+respirator',
        r'\bschimb\s+de\s+gaze', r'\bhematoz[ăa]',
        r'\baparat\s+respirator',
    ]),
    ('sistem_excretor', [
        r'\bexcre[tţț]', r'\brinichi', r'\brena', r'\bnefron',
        r'\burin[ăa]\b', r'\burinar', r'\bvezic[ăa]\s+urinar',
        r'\buretră', r'\buretra\b', r'\bureter',
        r'\bfiltra[rtţ]', r'\breabsorb', r'\bglomerul',
        r'\bcapsul[ăa]\s+Bowman', r'\btub\s+contort',
        r'\beliminar', r'\baparat\s+excretor',
    ]),
    ('sistem_reproducator', [
        r'\breproducă', r'\breproduct', r'\bovul\b', r'\bovar\b', r'\bovare',
        r'\bspermatozoid', r'\btesticul', r'\buter\b', r'\buterul\b',
        r'\bplacent', r'\bembrion', r'\bfătul?\b', r'\bfat\b',
        r'\bfecund', r'\bmenstr', r'\bpubertat', r'\bsarcin',
        r'\bnaşter', r'\bnaster', r'\bgameti?\b', r'\bgonad',
        r'\bgenital', r'\btrompa?\s+uterin', r'\bovulaţi', r'\bovulati',
        r'\bspermato', r'\bovogene', r'\bmeioză', r'\bmeioza\b',
    ]),
    ('genetica', [
        r'\bADN\b', r'\bARN\b', r'\bgene?\b', r'\bgena\b', r'\bgenă',
        r'\bcromozom', r'\bnucleotid', r'\breplicat',
        r'\btranscripti', r'\btranscripţi', r'\btraducere\b', r'\btranslati',
        r'\bribozom', r'\bprotein[ăa]', r'\baminoacid',
        r'\bcodon', r'\banticodon', r'\bbicatenar', r'\bmonocatenar',
        r'\bmutaţi', r'\bmutati', r'\bfenotip', r'\bgenotip',
        r'\brecesiv', r'\bdominant', r'\bheterozigot', r'\bhomozigot',
        r'\bhibrid', r'\bmonohibrid', r'\bdihibrid',
        r'\bîncrucişare', r'\bincrucisar',
        r'\blegile?\s+lui\s+Mendel', r'\bereditar',
        r'\bcariotip', r'\bgenom', r'\balel[eă]',
        r'\bsinte[sz]a?\s+(unei?\s+)?protein',
        r'\bcaten[ăa]\s+de\s+ADN',
    ]),
    ('ecologie_umana', [
        r'\becosistem', r'\bbiocenoză', r'\bbiocenoza\b', r'\bbiotop',
        r'\bpopulaţi[ei]', r'\bpopulati[ei]', r'\bhabitat',
        r'\bfactor\w*\s+ecologic', r'\bfactor\w*\s+abiot', r'\bfactor\w*\s+biot',
        r'\bpoluar', r'\bpoluant', r'\bdeşeuri', r'\bdeseuri',
        r'\becologi', r'\bbiodiversitat', r'\bspecii\b',
        r'\bproducător', r'\bconsumator', r'\bdescompunător',
        r'\blanţ\s+trofic', r'\blant\s+trofic', r'\breţea?\s+trofic',
        r'\bnişă\s+ecologic', r'\bnisa\s+ecologic',
        r'\bmediu\s+de\s+viaţă', r'\bmediu\s+ambiant',
    ]),
    ('alcatuirea_corpului', [
        r'\bcelul[ăa]', r'\bţesut', r'\btesut', r'\borgan\b', r'\borgane\b',
        r'\baparatul?\b', r'\bsistemul?\b',
        r'\bmembrana?\s+celular', r'\bnucle[ul]', r'\bcitoplasm',
        r'\borganit', r'\bmitocondri', r'\bribozom',
        r'\bcelula?\s+eucario', r'\bcelula?\s+procario',
        r'\bţesut\s+epitelial', r'\bţesut\s+conjunctiv',
        r'\bţesut\s+muscular', r'\bţesut\s+nervos',
        r'\bnivel\s+de\s+organizare',
    ]),
]

# Compile all patterns for performance
_COMPILED_RULES = [
    (topic, [re.compile(p, re.IGNORECASE) for p in patterns])
    for topic, patterns in TOPIC_RULES
]


def classify_question(q: Dict) -> str:
    """
    Return the question_type for a question dict.

    Expected keys: subject, part_label, number, prompt
    """
    subj = q.get('subject', '').upper()
    part = (q.get('part_label') or '').upper()
    prompt = q.get('prompt', '').lower()

    # Subject I
    if subj == 'I':
        if part == 'A':
            return 'fill_blank'
        elif part == 'B':
            return 'short_answer'
        elif part == 'C':
            return 'multiple_choice'
        elif part == 'D':
            return 'true_false'

    # Subject II
    elif subj == 'II':
        return 'multi_part'

    # Subject III
    elif subj == 'III':
        if part == '2':
            # Check if this sub-part is the mini-essay
            if 'minieseu' in prompt or 'mini-eseu' in prompt:
                return 'essay'
            # The c sub-question of part 2 is typically the essay
            num = q.get('number', '').lower()
            if num == 'c' and ('minieseu' in prompt or 'noţiuni' in prompt
                               or 'notiuni' in prompt or 'enumer' in prompt):
                return 'essay'
            return 'multi_part'
        else:
            return 'multi_part'

    # Fallback
    return 'short_answer'


def classify_topic(question_text: str, context: Optional[str] = None,
                   barem_answer: Optional[str] = None) -> str:
    """
    Classify the biology topic of a question using keyword matching.

    Args:
        question_text: The question prompt
        context: Optional context/preamble for the question
        barem_answer: The barem answer text

    Returns:
        One of the VALID_TOPICS enum values
    """
    # Combine all available text for matching
    combined = question_text or ''
    if context:
        combined += ' ' + context
    if barem_answer:
        combined += ' ' + barem_answer

    if not combined.strip():
        return 'altele'

    # Score each topic by counting matching patterns
    scores: Dict[str, int] = {}
    for topic, patterns in _COMPILED_RULES:
        count = 0
        for pat in patterns:
            matches = pat.findall(combined)
            count += len(matches)
        if count > 0:
            scores[topic] = count

    if not scores:
        return 'altele'

    # Sort by score descending
    sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # If top two are close (within 2 hits) and both have 3+ hits, mark as mixt
    if len(sorted_topics) >= 2:
        top_score = sorted_topics[0][1]
        second_score = sorted_topics[1][1]
        if top_score >= 3 and second_score >= 3 and (top_score - second_score) <= 2:
            # Check if they're from different major systems (not just related)
            t1, t2 = sorted_topics[0][0], sorted_topics[1][0]
            related_pairs = {
                frozenset({'sistem_osos', 'sistem_muscular'}),
                frozenset({'sistem_nervos', 'analizatori'}),
            }
            if frozenset({t1, t2}) not in related_pairs:
                return 'mixt'

    return sorted_topics[0][0]
