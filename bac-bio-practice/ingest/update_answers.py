"""
One-time script to populate correct answers for Subiectul I-A (fill_blank)
and I-B (short_answer) questions where the barem only contains scoring info
but not the actual correct terms.

Usage:
    cd /Users/alexandrapop/BAC/bac_webapp/bac-bio-practice
    source ../venv/bin/activate
    python -m ingest.update_answers
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "questions.db")

# ============================================================
# SUBIECTUL I-A: Fill-in-the-blank answers
# Each entry: question_id -> correct answer text
# ============================================================
IA_ANSWERS = {
    # 2020 tests
    "c967390b6c7adb59": "sistemul nervos central (SNC); sistemul nervos periferic (SNP)",
    "270d7d7ccd097d59": "vitală; curent",
    "9f969d9366efa485": "funcțional; parasimpatic",
    "de525837601e10fa": "metatarsienele; tarsienele (se acceptă orice două oase ale membrului inferior, ex: femurul, tibia, peroneul)",
    "1a714d2aff374dc3": "drept; neoxigenat (venos)",
    "5c3689b57cad3180": "periferic; organul Corti (celulele auditive din organul Corti)",
    "02490190da4296d1": "curent; vitale",
    "ef7de5d26e848a42": "vitală; curent",
    "2551b2652da53727": "neoxigenat (venos); oxigenat (arterial)",
    "1f6171707c16988d": "metatarsienele; falangele (se acceptă orice două oase ale membrului inferior)",
    "8ac4571833b21274": "parasimpaticul; vegetativ (autonom)",
    "43994ce260d7898b": "reabsorbția tubulară; secreția tubulară",
    "dfabae1c183065c1": "bicepsul; tricepsul (se acceptă orice doi mușchi scheletici: deltoidul, trapezul, cvadricepsul, etc.)",
    "acbd00ca428dc0ab": "endocrin; diabetului zaharat",
    "e38b5f8871c45c3d": "spermatozoizii (gameții masculini); testiculelor (gonadelor masculine). Se acceptă și: ovulele; ovarelor.",
    "e147a7654d02bddf": "funcțional; vegetativ (autonom)",
    "467ee06c1cb10e32": "nefrita (sau glomerulonefrita, litiaza renală, insuficiența renală); excretor (urinar)",
    "ffa86ac4a96c7338": "osos; nervos",
    "77dac5aabe2af6be": "trunchiului; membrelor",
    "e26a3bb6f32be6ec": "nutriție; circulator",
    "578217d5a4f41cfa": "circulator; respirator (se acceptă și excretor, oricare două din: circulator, respirator, excretor)",
    "c65bf160dc48c32a": "diurne (cromatice); nocturne (acromatice/crepusculare)",
    "c720d97b66a5e182": "parasimpaticul; vegetativ (autonom)",
    # 2021 tests
    "db29aad3682de139": "plămânii; toracică",
    "5e82547e533b0834": "topografic; central",
    "c7512fd3366879f6": "superioară; inferioară",
    "0d831e2b16a3cae7": "tensiunea arterială; frecvența cardiacă (pulsul). Se acceptă și: debitul cardiac.",
    "1d3edcd751694f0f": "pulmonară totală; rezidual",
    "f0a9ca245e65ee01": "frecvența cardiacă (pulsul); debitul cardiac",
    "eac2b23597d266d1": "periferic; organul Corti (celulele auditive din urechea internă)",
    "5a1a22eafe96fe88": "proteinelor (sau lipidelor, glucidelor); intestinul subțire. Se acceptă orice produs final corect asociat cu locul obținerii.",
    "cb33c6cc0536e202": "periferic; celulele senzoriale din canalele semicirculare (crestele ampulare / maculele)",
    "38fe955dfc01aed8": "diabetul zaharat (sau nanismul, gigantismul, mixedemul); endocrine",
    "4333cd425f1a0935": "bila; lipidelor (grăsimilor)",
    "cb04b55a3b47e3bc": "etmoidul (sau frontalul, occipitalul, parietalul, temporalul); capului (neurocraniului)",
    "80ef807b207773b4": "oxigenat (arterial); artera aortă",
    "c7fdd2735ebaa51d": "bastonașe; pigmenți fotosensibili",
    "4af3c1be19b3b84c": "metacarpienele (sau carpienele); superior. Se acceptă și: metatarsienele (tarsienele); inferior.",
    "e8ba8913a67762fa": "pulmonare; oxigenat (arterial)",
    # 2022 tests
    "83ad2c7b426c899e": "neoxigenat (venos); artera pulmonară",
    "cd246b79010f3875": "proteinelor → aminoacizii; lipidelor → acizi grași și glicerol; glucidelor → glucoza. Se acceptă orice pereche corectă.",
    "945185135a1ea049": "nervos; relaţie",
    "6d2c1b89d63016ea": "vizual; aria vizuală din lobul occipital al cortexului cerebral",
    "d2078fe842066d2f": "stâng; artera aortă",
    # 2023 tests
    "ff5e48d27cccb4c8": "osos; nervos",
    "e8197ec54e430950": "frecvența cardiacă (pulsul); debitul cardiac",
    "95a127d5b7cbcbb9": "bicepșii; tricepșii (se acceptă orice doi mușchi scheletici: deltoidul, trapezul, cvadricepsul, croitorul, etc.)",
    "d3effd685df8a4ec": "tibia; peroneul (fibula). Se acceptă și: rotula (patela), tarsienele, metatarsienele, falangele.",
    "f4e6bbfd1aed2f53": "cistita (sau litiaza renală, insuficiența renală, pielonefrita); excretor (urinar)",
    # 2024 tests
    "1b7aabba7e2cd9c4": "vezica urinară; uretră",
    "4413538655349442": "endocrin; reglare. Se acceptă și: muscular; relaţie.",
    "335ec46906741a22": "sensibilitatea (senzitivitatea); motricitatea voluntară",
    "437b5e218b6b66fc": "volumul; crește",
    "fa00560a11b4cba1": "glaucomul (sau miopia, hipermetropia, astigmatismul, daltonismul, conjunctivita); analizatorului vizual (ochiului)",
    # 2025 tests
    "911d92acd4aa824c": "diabetul zaharat; nanismul (se acceptă orice două disfuncții endocrine: gigantismul, acromegalia, mixedemul, gușa endemică, etc.)",
    "9e49fd4a4e4172f5": "poluarea chimică; poluarea fizică (sonoră/termică/radioactivă)",
    "edbd1c3dc4aa62f2": "metacarpienele (sau carpienele); superior. Se acceptă și: metatarsienele (tarsienele); inferior.",
    "8d80a6a120034186": "metacarpienele; superior",
    # 2026 tests
    "2485e8717b16eb04": "inspirației; scade",
    "3af878531f7a9e88": "atriul; venele cave",
    # BAC 2025 model
    "83c76f38be636bbc": "volumul expirator de rezervă; volumul rezidual",
    # Regional simulations
    "074cff3522abe960": "leucemiile (sau hemofilia, tromboza); circulator (sanguin/cardiovascular)",
    "678af47aee05fec5": "mimicii (feței); masticatori",
    "8905f162ed7dfa9a": "temporalele; parietalele",
    "2c53b5add1289184": "autoreplicarea (replicarea); codificarea (stocarea) informației genetice",
    "587bf2ecf0e60c6c": "superioară; inferioară",
    "54ba149d60a22d58": "stern; coaste (12 perechi de coaste)",
    "8486680b844c9b8b": "funcțional; vegetativ (autonom)",
    "b6c91c56bc1ecf72": "vitală; curent",
}

# ============================================================
# SUBIECTUL I-B: Short answer with example correct answers
# ============================================================
IB_ANSWERS = {
    # 2020 tests
    "dee3dcbfd75af107": (
        "B 6 puncte\n"
        "- numirea a două afecțiuni ale sistemului muscular; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei afecțiuni numite cu câte o caracteristică a acesteia; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Distrofia musculară – slăbirea progresivă a mușchilor scheletici\n"
        "2. Miastenia – scăderea forței de contracție musculară\n"
        "Se acceptă și: crampe musculare, tetania, atrofia musculară, miopatii, etc."
    ),
    "d5b73a9015d649c1": (
        "B 6 puncte\n"
        "- numirea celor două tipuri de celule fotoreceptoare din retină; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărui tip de celulă fotoreceptoare cu rolul său; 2 x 2p.= 4 puncte\n\n"
        "Răspunsuri corecte:\n"
        "1. Celulele cu conuri – receptori ai vederii diurne (cromatice/colorate), permit distingerea culorilor\n"
        "2. Celulele cu bastonașe – receptori ai vederii nocturne (crepusculare/acromatice)"
    ),
    "8a7b04e02b4d2476": (
        "B 6 puncte\n"
        "- numirea unei afecțiuni a sistemului osos și unei afecțiuni a sistemului muscular; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei afecțiuni numite cu câte o caracteristică; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Osteoporoza (sistem osos) – scăderea densității osoase, fragilitate osoasă\n"
        "2. Distrofia musculară (sistem muscular) – slăbirea progresivă a mușchilor\n"
        "Se acceptă: fracturi, luxații, entorse, scolioză (osos); crampe, miastenie, atrofie (muscular)"
    ),
    "c9578f9db7964444": (
        "B 6 puncte\n"
        "- numirea a două organe din cavitatea abdominală; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărui organ cu efectul stimulării simpaticului asupra organului; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Stomacul – inhibarea peristaltismului și a secreției gastrice\n"
        "2. Ficatul – stimularea glicogenolizei (eliberarea glucozei în sânge)\n"
        "Se acceptă și: intestinul (inhibarea peristaltismului), vezica urinară (relaxarea mușchiului detrusor)"
    ),
    "c0a3f2dd3696945d": (
        "B 6 puncte\n"
        "- numirea a două disfuncții ale tiroidei; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei disfuncții tiroidiene cu o cauză a ei; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Gușa endemică – deficit de iod în alimentație\n"
        "2. Boala Basedow-Graves (hipertiroidism) – hipersecreția de tiroxină\n"
        "Se acceptă și: mixedemul – hiposecreția de tiroxină la adult; cretinismul – hiposecreția de tiroxină în copilărie"
    ),
    "3abf02b3d3da856f": (
        "B 6 puncte\n"
        "- numirea a două căi ascendente cu rol în conducerea măduvei spinării; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei căi cu rolul său; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Fasciculul Goll (gracilis) – conducerea sensibilității tactile fine și proprioceptive de la membrele inferioare\n"
        "2. Fasciculul spinotalamic lateral – conducerea sensibilității dureroase și termice"
    ),
    "6d04af0a92f83838": (
        "B 6 puncte\n"
        "- numirea a două afecțiuni ale analizatorului vizual; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei afecțiuni cu o caracteristică; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Miopia – vederea clară a obiectelor apropiate, imaginea se formează în fața retinei\n"
        "2. Hipermetropia – vederea clară a obiectelor depărtate, imaginea se formează în spatele retinei\n"
        "Se acceptă și: astigmatismul, cataracta, glaucomul, daltonismul, conjunctivita"
    ),
    "8143236159017580": (
        "B 6 puncte\n"
        "- numirea a două boli endocrine; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei boli cu dereglarea hormonală care a provocat-o; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Diabetul zaharat – hiposecreția de insulină (de către pancreasul endocrin)\n"
        "2. Gigantismul – hipersecreția de somatotrop (STH) în copilărie\n"
        "Se acceptă și: nanismul (hiposecreție STH), acromegalia (hipersecreție STH la adult), gușa (deficit iod/tiroxină)"
    ),
    "7a491d6a7c0c2df5": (
        "B 6 puncte\n"
        "- numirea a două organe din cavitatea abdominală; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărui organ cu câte un rol; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Stomacul – digestia mecanică și chimică a alimentelor (secreția sucului gastric)\n"
        "2. Ficatul – secreția bilei, detoxifierea organismului\n"
        "Se acceptă și: intestinul subțire (absorbția nutrienților), rinichii (filtrarea sângelui), pancreasul (secreția sucului pancreatic)"
    ),
    "d6178d98bfda2d77": (
        "B 6 puncte\n"
        "- numirea a două căi cu rol în conducerea măduvei spinării; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei căi cu rolul său; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Fasciculul piramidal (corticospinal) – cale descendentă, conducerea comenzilor motorii voluntare\n"
        "2. Fasciculul spinotalamic – cale ascendentă, conducerea sensibilității dureroase și termice"
    ),
    # 2020 continued
    "b2b49e5c0e2e4d83": (
        "B 6 puncte\n"
        "- numirea a două tipuri de contracții musculare; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărui tip cu o caracteristică; 2 x 2p.= 4 puncte\n\n"
        "Răspunsuri corecte:\n"
        "1. Contracția izotonică – se modifică lungimea mușchiului, tonusul rămâne constant\n"
        "2. Contracția izometrică – se modifică tonusul mușchiului, lungimea rămâne constantă"
    ),
    "a87b4e964f754ff6": (
        "B 6 puncte\n"
        "- numirea a două organe ale sistemului reproducător masculin; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărui organ cu câte un rol; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Testiculele – producerea spermatozoizilor (spermatogeneză) și secreția de testosteron\n"
        "2. Prostata – secreția lichidului prostatic, componentă a lichidului seminal\n"
        "Se acceptă și: epididimul (maturarea spermatozoizilor), canalele deferente (transportul spermatozoizilor), veziculele seminale"
    ),
    "ade7e47b5e9e8ed3": (
        "B 6 puncte\n"
        "- numirea a două organe ale sistemului reproducător feminin; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărui organ cu câte un rol; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Ovarele – producerea ovulelor (ovogeneză) și secreția de estrogen/progesteron\n"
        "2. Uterul – locul implantării embrionului și dezvoltării fătului\n"
        "Se acceptă și: trompele uterine (transportul ovulului, locul fecundației), vaginul"
    ),
    "ea9d0f27f6b5b0c7": (
        "B 6 puncte\n"
        "- numirea a două afecțiuni ale sistemului osos; 2 x 1p.= 2 puncte\n"
        "- asocierea fiecărei afecțiuni cu o caracteristică; 2 x 2p.= 4 puncte\n\n"
        "Exemple de răspunsuri corecte:\n"
        "1. Osteoporoza – scăderea densității osoase, fragilitate osoasă crescută\n"
        "2. Fractura – ruperea continuității osului în urma unui traumatism\n"
        "Se acceptă și: luxația, entorsa, scolioza, cifoza, lordoza, rahitismul, artrita"
    ),
}

# For I-B questions we don't have specific IDs for, we'll need to fetch and match
# Let's handle the remaining ones by fetching all and updating based on prompt patterns


def get_ib_example_answer(prompt: str) -> str:
    """Generate example correct answer for I-B questions based on prompt content."""
    p = prompt.lower()

    if 'afecțiuni' in p or 'afecţiuni' in p or 'boli' in p or 'disfuncți' in p or 'disfuncţi' in p:
        if 'muscular' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Distrofia musculară – slăbirea progresivă a mușchilor scheletici\n"
                "2. Miastenia – scăderea forței de contracție musculară\n"
                "Se acceptă și: crampe musculare, tetania, atrofia musculară"
            )
        elif 'osos' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Osteoporoza – scăderea densității osoase\n"
                "2. Fractura – ruperea continuității osului\n"
                "Se acceptă și: luxația, entorsa, scolioza, rahitismul, artrita"
            )
        elif 'nervos' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Epilepsia – crize convulsive cauzate de descărcări neuronale anormale\n"
                "2. Meningita – inflamarea meningelor\n"
                "Se acceptă și: Parkinson, Alzheimer, AVC, nevralgia, poliomielita"
            )
        elif 'vizual' in p or 'ochi' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Miopia – imaginea se formează în fața retinei, vederea la distanță este afectată\n"
                "2. Cataracta – opacifierea cristalinului\n"
                "Se acceptă și: hipermetropia, astigmatismul, glaucomul, daltonismul, conjunctivita"
            )
        elif 'auditiv' in p or 'ureche' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Otita – inflamarea urechii medii\n"
                "2. Surditatea – pierderea parțială sau totală a auzului\n"
                "Se acceptă și: labirintita, perforarea timpanului"
            )
        elif 'endocrin' in p or 'tiroid' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Diabetul zaharat – hiposecreția de insulină\n"
                "2. Gușa endemică – deficit de iod în alimentație\n"
                "Se acceptă și: gigantismul, nanismul, acromegalia, boala Basedow, mixedemul"
            )
        elif 'excretor' in p or 'urinar' in p or 'rinichi' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Nefrita – inflamarea rinichilor\n"
                "2. Cistita – inflamarea vezicii urinare\n"
                "Se acceptă și: glomerulonefrita, litiaza renală, insuficiența renală, pielonefrita"
            )
        elif 'circulator' in p or 'cardiovascular' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Anemia – scăderea numărului de eritrocite sau a hemoglobinei\n"
                "2. Leucemia – proliferarea necontrolată a leucocitelor\n"
                "Se acceptă și: hemofilia, tromboza, ateroscleroza, infarctul miocardic"
            )
        elif 'digestiv' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Ulcerul gastric – leziunea mucoasei stomacului\n"
                "2. Hepatita – inflamarea ficatului\n"
                "Se acceptă și: gastrita, ciroza, apendicita, colelitiaza"
            )
        elif 'respirator' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Astmul bronșic – obstrucția reversibilă a căilor respiratorii\n"
                "2. Pneumonia – inflamarea plămânilor\n"
                "Se acceptă și: bronșita, emfizemul, tuberculoza, laringita"
            )
        elif 'reproducă' in p or 'genital' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Anexita – inflamarea trompelor uterine\n"
                "2. Prostatita – inflamarea prostatei\n"
                "Se acceptă și: endometrioza, fibroame uterine, orhita"
            )
        else:
            return (
                "Exemple de răspunsuri corecte:\n"
                "Se acceptă orice două afecțiuni relevante, corect numite, "
                "fiecare asociată cu o caracteristică/cauză/simptom specific(ă)."
            )

    if 'contracți' in p or 'contracţi' in p:
        return (
            "Răspunsuri corecte:\n"
            "1. Contracția izotonică – se modifică lungimea mușchiului, tonusul rămâne constant\n"
            "2. Contracția izometrică – se modifică tonusul mușchiului, lungimea rămâne constantă"
        )

    if 'fotoreceptoare' in p or 'celule cu conuri' in p or 'celulele cu bastonaș' in p:
        return (
            "Răspunsuri corecte:\n"
            "1. Celulele cu conuri – receptori ai vederii diurne/cromatice\n"
            "2. Celulele cu bastonașe – receptori ai vederii nocturne/acromatice"
        )

    if 'organe' in p and ('abdominală' in p or 'abdominal' in p):
        if 'simpatic' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Stomacul – inhibarea peristaltismului și a secreției gastrice\n"
                "2. Ficatul – stimularea glicogenolizei\n"
                "Se acceptă și: intestinul (inhibare peristaltism), vezica urinară (relaxare detrusor)"
            )
        elif 'parasimpatic' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Stomacul – stimularea peristaltismului și a secreției gastrice\n"
                "2. Intestinul – stimularea peristaltismului intestinal\n"
                "Se acceptă și: vezica urinară (contracția detrusorului)"
            )
        else:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Stomacul – digestia mecanică și chimică a alimentelor\n"
                "2. Ficatul – secreția bilei, detoxifierea organismului\n"
                "Se acceptă: intestinul subțire, rinichii, pancreasul, splina, etc."
            )

    if 'organe' in p and ('toracică' in p or 'toracica' in p):
        return (
            "Exemple de răspunsuri corecte:\n"
            "1. Inima – pomparea sângelui în circulație\n"
            "2. Plămânii – realizarea schimbului de gaze (hematoză pulmonară)"
        )

    if ('căi' in p or 'cai' in p) and ('măduvei' in p or 'măduvă' in p or 'maduv' in p):
        if 'ascendent' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Fasciculul Goll (gracilis) – conducerea sensibilității tactile fine de la membrele inferioare\n"
                "2. Fasciculul spinotalamic lateral – conducerea sensibilității dureroase și termice"
            )
        elif 'descendent' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Fasciculul piramidal (corticospinal) – conducerea comenzilor motorii voluntare\n"
                "2. Fasciculul rubrospinal – conducerea tonusului muscular"
            )
        else:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Fasciculul piramidal (corticospinal) – cale descendentă, comenzi motorii voluntare\n"
                "2. Fasciculul spinotalamic – cale ascendentă, sensibilitate dureroasă și termică"
            )

    if 'mușchi' in p or 'muschi' in p or 'muşchi' in p:
        if 'capul' in p or 'cap' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Mușchii masticatori (temporalul, maseterul) – realizarea masticației\n"
                "2. Mușchii mimicii (orbicularul buzelor, frontalul) – realizarea expresiilor faciale"
            )
        elif 'membrului superior' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Bicepsul brahial – flexia antebrațului pe braț\n"
                "2. Tricepsul brahial – extensia antebrațului\n"
                "Se acceptă și: deltoidul, mușchii antebrațului"
            )
        elif 'membrului inferior' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Cvadricepsul femural – extensia gambei pe coapsă\n"
                "2. Bicepsul femural – flexia gambei pe coapsă\n"
                "Se acceptă și: croitorul, mușchii gambei"
            )
        else:
            return (
                "Exemple de răspunsuri corecte:\n"
                "Se acceptă orice doi mușchi scheletici corect numiți (biceps, triceps, deltoid, "
                "trapez, cvadriceps, croitor, etc.), fiecare asociat cu rolul/localizarea sa."
            )

    if 'reproducător' in p or 'reproducator' in p or 'genital' in p:
        if 'masculin' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Testiculele – producerea spermatozoizilor și secreția de testosteron\n"
                "2. Prostata – secreția lichidului prostatic\n"
                "Se acceptă și: epididimul, canalele deferente, veziculele seminale, penisul"
            )
        elif 'feminin' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Ovarele – producerea ovulelor și secreția de estrogen/progesteron\n"
                "2. Uterul – locul implantării embrionului\n"
                "Se acceptă și: trompele uterine, vaginul"
            )
        else:
            return (
                "Exemple de răspunsuri corecte:\n"
                "Se acceptă orice două organe ale sistemului reproducător, "
                "corect asociate cu câte un rol al lor."
            )

    if 'hormon' in p:
        if 'hipofiz' in p or 'adenohipofiz' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Somatotropul (STH) – stimularea creșterii organismului\n"
                "2. Tireotropul (TSH) – stimularea activității glandei tiroide\n"
                "Se acceptă și: FSH, LH, ACTH, prolactina"
            )
        elif 'suprarenal' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Adrenalina – creșterea frecvenței cardiace, mobilizarea glucozei\n"
                "2. Cortizolul – reglarea metabolismului glucidic, efect antiinflamator"
            )
        elif 'tiroid' in p:
            return (
                "Exemple de răspunsuri corecte:\n"
                "1. Tiroxina (T4) – stimularea metabolismului bazal\n"
                "2. Triiodotironina (T3) – stimularea metabolismului celular"
            )
        else:
            return (
                "Exemple de răspunsuri corecte:\n"
                "Se acceptă orice doi hormoni corect numiți, fiecare asociat "
                "cu glanda care îl secretă sau cu rolul/efectul său."
            )

    if 'glande endocrine' in p or 'gland' in p:
        return (
            "Exemple de răspunsuri corecte:\n"
            "1. Tiroida – situată în regiunea cervicală, anterior, secretă tiroxina\n"
            "2. Suprarenalele – situate deasupra rinichilor, secretă adrenalina și cortizolul\n"
            "Se acceptă și: pancreasul endocrin, hipofiza, epifiza, timusul, gonadele"
        )

    if 'sucuri digestive' in p or 'suc digestiv' in p or 'secreți' in p:
        return (
            "Exemple de răspunsuri corecte:\n"
            "1. Sucul gastric – secretat de stomac, conține pepsina și HCl\n"
            "2. Sucul pancreatic – secretat de pancreas, conține tripsina, lipaza, amilaza\n"
            "Se acceptă și: bila, sucul intestinal, saliva"
        )

    if 'volume respiratorii' in p or 'volum' in p:
        return (
            "Exemple de răspunsuri corecte:\n"
            "1. Volumul curent – volumul de aer inspirat/expirat în repaus (~500 ml)\n"
            "2. Volumul inspirator de rezervă – volumul suplimentar inspirat forțat\n"
            "Se acceptă și: volumul expirator de rezervă, volumul rezidual"
        )

    if 'componente' in p and 'ecosistem' in p:
        return (
            "Răspunsuri corecte:\n"
            "1. Biotopul – componenta abiotică (mediul fizico-chimic)\n"
            "2. Biocenoza – componenta biotică (totalitatea organismelor vii)"
        )

    if 'segment' in p and ('membrului' in p or 'membru' in p):
        return (
            "Exemple de răspunsuri corecte:\n"
            "Se acceptă orice două segmente ale membrului, fiecare asociat cu un os:\n"
            "- Brațul – humerus\n- Antebrațul – radius și ulna\n- Mâna – carpiene, metacarpiene, falange\n"
            "- Coapsa – femur\n- Gamba – tibia și peroneul\n- Piciorul – tarsiene, metatarsiene, falange"
        )

    if 'sintez' in p and ('protein' in p or 'ARN' in p):
        return (
            "Răspunsuri corecte:\n"
            "1. Transcripția – sinteza ARNm după modelul ADN, are loc în nucleu\n"
            "2. Traducerea (translația) – sinteza lanțului polipeptidic după ARNm, are loc la ribozomi"
        )

    if 'vase de sânge' in p or 'vase de sange' in p:
        return (
            "Exemple de răspunsuri corecte:\n"
            "1. Arterele – transportă sângele de la inimă spre organe, pereți groși și elastici\n"
            "2. Venele – transportă sângele de la organe spre inimă, pereți subțiri, au valve\n"
            "Se acceptă și: capilarele – vase foarte fine, permit schimbul de substanțe"
        )

    # Generic fallback
    return (
        "Se acceptă orice două răspunsuri corecte din punct de vedere științific, "
        "fiecare corect asociat cu o caracteristică/rol/cauză relevantă."
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update I-A answers
    print("=== Updating Subiectul I-A answers ===")
    updated_ia = 0
    for q_id, answer in IA_ANSWERS.items():
        # Build the new barem with the actual answer
        new_barem = (
            f"Răspunsul corect: {answer}\n\n"
            "Notare: Se acordă câte 2p. pentru fiecare noțiune corectă. "
            "2 x 2p. = 4 puncte. Se acceptă orice formulare echivalentă."
        )
        cursor.execute(
            "UPDATE questions SET barem_answer = ? WHERE id = ?",
            (new_barem, q_id),
        )
        if cursor.rowcount > 0:
            updated_ia += 1
    print(f"  Updated {updated_ia} I-A questions")

    # Update I-B answers
    print("\n=== Updating Subiectul I-B answers ===")
    updated_ib = 0

    # First, apply specific overrides
    for q_id, answer in IB_ANSWERS.items():
        cursor.execute(
            "UPDATE questions SET barem_answer = ? WHERE id = ?",
            (answer, q_id),
        )
        if cursor.rowcount > 0:
            updated_ib += 1

    # Then, handle remaining I-B questions that don't have specific overrides
    cursor.execute(
        "SELECT id, prompt, barem_answer FROM questions "
        "WHERE subject = 'I' AND part_label = 'B' AND id NOT IN ({})".format(
            ','.join('?' * len(IB_ANSWERS))
        ),
        list(IB_ANSWERS.keys()),
    )
    remaining = cursor.fetchall()

    for q_id, prompt, old_barem in remaining:
        example = get_ib_example_answer(prompt)
        # Append examples to existing barem
        new_barem = f"{old_barem}\n\n{example}"
        cursor.execute(
            "UPDATE questions SET barem_answer = ? WHERE id = ?",
            (new_barem, q_id),
        )
        if cursor.rowcount > 0:
            updated_ib += 1

    print(f"  Updated {updated_ib} I-B questions")

    conn.commit()
    conn.close()

    print(f"\nTotal updated: {updated_ia + updated_ib} questions")
    print("Done.")


if __name__ == "__main__":
    main()
