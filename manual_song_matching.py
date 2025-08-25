#!/usr/bin/env python3
"""
Manual song matching using LLM understanding of the translations
"""

import re
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()

def parse_translation_file(filename: str) -> List[Dict]:
    """Parse the Italian-Google-Croatian translation file"""
    songs = []
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line_num, line in enumerate(lines[1:], 2):  # Skip header
        line = line.strip()
        if not line or line.startswith('|---'):
            continue
            
        # Split by | and clean up
        parts = [part.strip() for part in line.split('|')]
        if len(parts) >= 4:  # Should have empty, italian, google, croatian
            italian = parts[1].strip()
            google = parts[2].strip()
            croatian = parts[3].strip()
            
            # Extract ID from Italian song
            id_match = re.match(r'^(\d+)', italian)
            if id_match:
                song_id = id_match.group(1).zfill(3)  # Pad with zeros
                songs.append({
                    'id': song_id,
                    'italian': italian,
                    'google': google,
                    'croatian_from_file': croatian  # This is just the list, not matched
                })
    
    return songs

def get_parsed_croatian_songs(folder: str) -> List[str]:
    """Get all Croatian song titles from ChordPro files"""
    import os
    import glob
    
    songs = []
    pattern = os.path.join(folder, "*.chordpro")
    
    for filepath in glob.glob(pattern):
        filename = os.path.basename(filepath)
        # Extract title from filename (remove numbers and .chordpro)
        title = re.sub(r'^\d+-\d+-', '', filename)
        title = re.sub(r'\.chordpro$', '', title)
        songs.append(title)
    
    return sorted(songs)

def extract_italian_title(italian_text: str) -> str:
    """Extract just the title from Italian song format: 'ID - title - reference'"""
    # Split by ' - ' and take the title part (second part)
    parts = italian_text.split(' - ', 2)  # Split into max 3 parts
    if len(parts) >= 2:
        title = parts[1].strip()
        return title
    return italian_text.strip()  # Fallback to full text

def clean_croatian_title(croatian_text: str) -> str:
    """Remove Croatian biblical references"""
    if not croatian_text:
        return ""

    # For psalms: remove entire psalm reference like "- Ps 116 (117)"
    cleaned = re.sub(r'\s*-\s*Ps\s*\d+[^)]*\)\s*$', '', croatian_text)

    # For other biblical references: remove everything in parentheses at the end
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)

    # Remove any remaining biblical references at the end
    cleaned = re.sub(r'\s*-\s*[A-Z][a-z]*\s*\d+.*$', '', cleaned)

    return cleaned.strip()

def clean_google_translation(google_text: str) -> str:
    """Remove biblical references from Google translation"""
    if not google_text:
        return ""

    # Extract just the title part (remove ID and reference)
    # Format: "166 - Uzmi me u nebo - Vidi Fil 1:23"
    parts = google_text.split(' - ', 2)  # Split into max 3 parts
    if len(parts) >= 2:
        title = parts[1].strip()  # Take the middle part (the actual title)
        return title

    return google_text.strip()  # Fallback to full text

def normalize_biblical_reference(ref: str) -> str:
    """Normalize biblical reference for cross-language comparison using LLM understanding"""
    if not ref:
        return ""

    # Remove punctuation and normalize spaces
    normalized = re.sub(r'[,\.\-\s]+', ' ', ref).strip().upper()

    # Extract book abbreviation and numbers
    match = re.match(r'([A-Z]+)\s*(\d+.*)', normalized)
    if match:
        book_abbrev, numbers = match.groups()

        # Use LLM knowledge to normalize common biblical book abbreviations to English
        # This approach will work for any language pair
        book_mappings = {
            # Old Testament
            'GN': 'GEN', 'POST': 'GEN',  # Genesis
            'ES': 'EXO', 'IZL': 'EXO',   # Exodus
            'LV': 'LEV',                  # Leviticus
            'NM': 'NUM', 'BR': 'NUM',    # Numbers
            'DT': 'DEU', 'PNZ': 'DEU',   # Deuteronomy
            'GS': 'JOS', 'JŠ': 'JOS',    # Joshua
            'GDC': 'JDG', 'SUCI': 'JDG', # Judges
            'RT': 'RUT', 'RUT': 'RUT',   # Ruth
            'SAL': 'PSA', 'PS': 'PSA',   # Psalms
            'PR': 'PRO', 'IZREKE': 'PRO', # Proverbs
            'QO': 'ECC', 'PROP': 'ECC',  # Ecclesiastes
            'CT': 'SNG', 'PJ': 'SNG',    # Song of Songs
            'IS': 'ISA', 'IZ': 'ISA',    # Isaiah
            'JER': 'JER',                 # Jeremiah
            'EZ': 'EZK',                  # Ezekiel
            'DN': 'DAN',                  # Daniel
            'OS': 'HOS', 'HOŠ': 'HOS',   # Hosea
            'GL': 'JOL', 'JL': 'JOL',    # Joel
            'AM': 'AMO',                  # Amos
            'ABD': 'OBA',                 # Obadiah
            'GNA': 'JON', 'JON': 'JON',  # Jonah
            'MI': 'MIC', 'MIH': 'MIC',   # Micah
            'NA': 'NAH', 'NAH': 'NAH',   # Nahum
            'AB': 'HAB', 'HAB': 'HAB',   # Habakkuk
            'SOF': 'ZEP', 'SEF': 'ZEP',  # Zephaniah
            'AG': 'HAG', 'HAG': 'HAG',   # Haggai
            'ZC': 'ZEC', 'ZAH': 'ZEC',   # Zechariah
            'ML': 'MAL', 'MAL': 'MAL',   # Malachi

            # New Testament
            'MT': 'MAT',                  # Matthew
            'MC': 'MRK', 'MK': 'MRK',    # Mark
            'LC': 'LUK', 'LK': 'LUK',    # Luke
            'GV': 'JHN', 'IV': 'JHN',    # John
            'AT': 'ACT', 'DJ': 'ACT',    # Acts
            'RM': 'ROM', 'RIM': 'ROM',   # Romans
            'COR': 'COR', 'KOR': 'COR',  # Corinthians
            'GAL': 'GAL',                 # Galatians
            'EF': 'EPH',                  # Ephesians
            'FIL': 'PHP',                 # Philippians
            'COL': 'COL', 'KOL': 'COL',  # Colossians
            'TS': 'THS', 'TES': 'THS',   # Thessalonians
            'TM': 'TIM', 'TIM': 'TIM',   # Timothy
            'TT': 'TIT', 'TIT': 'TIT',   # Titus
            'FLM': 'PHM',                 # Philemon
            'EB': 'HEB', 'HEB': 'HEB',   # Hebrews
            'GC': 'JAS', 'JAK': 'JAS',   # James
            'PT': 'PET', 'PET': 'PET',   # Peter
            'GV': 'JHN', 'IV': 'JHN',    # John (epistles)
            'GD': 'JUD', 'JUD': 'JUD',   # Jude
            'AP': 'REV', 'OTK': 'REV',   # Revelation
        }

        # Normalize the book abbreviation
        normalized_book = book_mappings.get(book_abbrev, book_abbrev)
        return f"{normalized_book} {numbers}"

    return normalized

def extract_biblical_reference(text: str) -> str:
    """Extract biblical reference from song title"""
    # Look for patterns like "Cfr. Sal 25 (24)", "Ps 123 (122)", "Ode XL", etc.
    patterns = [
        r'Cfr\.\s*(.*?)$',  # Italian: Cfr. Nm 23,7-24 (capture everything after Cfr. until end)
        r'Vidi\s*([^-]+?)(?:\s*-|$)',   # Croatian: Vidi Ps 123 (122)
        r'-\s*(Ps\s*\d+[^)]*\))',  # Croatian: - Ps 123 (122)
        r'-\s*(Sal\s*\d+[^)]*\))', # Italian: - Sal 123 (122)
        r'\((.*?oda.*?)\)',  # Odes: (XL. Salomonova oda)
        r'(Ode\s*[IVX]+)',   # Italian Odes: Ode XL
        r'(\d+\s*Kor\s*\d+[^)]*)', # Corinthians: 1 Kor 13
        r'(Mt\s*\d+[^)]*)', # Matthew: Mt 5
        r'(Lk\s*\d+[^)]*)', # Luke: Lk 1
        r'(Iv\s*\d+[^)]*)', # John: Iv 14
        r'(Otk\s*\d+[^)]*)', # Revelation: Otk 7
        r'(Nm\s*\d+[^-]*)', # Numbers: Nm 23,7-24
        r'(Br\s*\d+[^)]*)', # Numbers Croatian: Br 23 7 - 24
        r'\(([^)]+)\)',  # Any reference in parentheses
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""

def extract_psalm_numbers(ref: str) -> tuple:
    """Extract psalm numbers from biblical reference"""
    if not ref:
        return None, None

    # Look for pattern like "Sal 25 (24)" or "Ps 123 (122)"
    match = re.search(r'(?:Sal|Ps)\s*(\d+)\s*\((\d+)\)', ref, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)

    # Look for simple pattern like "Ps 123"
    match = re.search(r'(?:Sal|Ps)\s*(\d+)', ref, re.IGNORECASE)
    if match:
        return match.group(1), None

    return None, None

def extract_google_title(google_text: str) -> str:
    """Extract just the title from Google translation format: 'ID - title - reference'"""
    if not google_text:
        return ""

    # Split by ' - ' and take the title part (second part)
    parts = google_text.split(' - ', 2)  # Split into max 3 parts
    if len(parts) >= 2:
        title = parts[1].strip()
        return title
    return google_text.strip()  # Fallback to full text

def calculate_similarity(italian_song: dict, croatian_song: str) -> float:
    """Calculate similarity between Italian and Croatian song using cleaned titles"""
    google_translate = italian_song['google']

    # Clean both titles by removing biblical references
    google_clean = clean_google_translation(google_translate) if google_translate else ""
    croatian_clean = clean_croatian_title(croatian_song)

    scores = []

    # 1. Direct similarity with cleaned titles
    if google_clean:
        scores.append(similarity(google_clean, croatian_clean))
        scores.append(similarity(google_clean, croatian_song))  # Also try with original Croatian

    # 2. Normalized similarity (remove punctuation, case)
    if google_clean:
        google_norm = re.sub(r'[^\w\s]', '', google_clean.upper())
        croatian_norm = re.sub(r'[^\w\s]', '', croatian_clean.upper())
        scores.append(similarity(google_norm, croatian_norm))

    # 3. Key word matching with cleaned titles
    if google_clean:
        google_words = set(re.findall(r'\b\w{3,}\b', google_clean.upper()))
        croatian_words = set(re.findall(r'\b\w{3,}\b', croatian_clean.upper()))
        if google_words and croatian_words:
            word_overlap = len(google_words & croatian_words) / len(google_words | croatian_words)
            scores.append(word_overlap)

    return max(scores) if scores else 0.0

def create_manual_matches() -> Dict[str, str]:
    """Create manual matches using LLM understanding of translations"""

    # Based on my analysis of Google translations and Croatian song patterns
    manual_matches = {
        # Psalm-based matches (clear biblical references)
        "001": "K TEBI UZDIŽEM SVOJE OČI - Ps 123 (122)",  # Tebi podižem oči svoje - Psalam 123
        "002": "K TEBI GOSPODINE UZDIŽEM SVOJU DUŠU - Ps 24 (25)",  # Tebi, Gospodine, uzdižem dušu svoju - Psalam 25
        "003": "TEBI GOSPODINE SVOJIM GLASOM VAPIJEM - Ps 141 (142)",  # K tebi, Gospodine, svojim glasom vapim za pomoć - Ps 142
        "004": "TEBE GOSPODINE TREBA SLAVITI NA SIONU - Ps 64 (65)",  # Tebi pripada hvala, Gospodine, na Sionu - Ps 65
        "007": "HVALITE JAHVU - Ps 135 (136)",  # Slavite Gospodina - Psalam 100
        "019": "PODIGNITE VRATA - Ps 23 (24)",  # Podignite se, o vrata - Psalam 24
        "020": "UZDIŽEM OČI SVOJE KA GORAMA - Ps 120 (121)",  # Podižem oči svoje prema planinama - Ps 121
        "022": "LJUBIM TE GOSPODINE - Ps 18",  # Ljubim Gospodina - Psalam 116

        # Clear title matches
        "005": "ABBA OČE (Rim 815 - 17)",  # Abba, Oče - Rm 8,15-17
        "006": "ABRAHAM (Post 181-6)",  # Abraham - Post 18,1-5
        "010": "JAGANJČE BOŽJI",  # Jaganjče Božji
        "011": "AKEDA ()",  # Akedà
        "021": "AMEN - AMEN - AMEN (Otk 7 12 - 14)",  # Amen, Amen, Amen - Otk 7,12-14
        "023": "IDITE I NAVIJESTITE MOJOJ BRAĆI (Mt 2816-20)",  # Idi i javi mojoj braći - Mt 28,7-10
        "025": "ZDRAVO MARIJO I",  # Zdravo Marijo I
        "026": "ZDRAVO MARIJO II",  # Ave Maria II
        "028": "BLAGOSLOVLJEN BUDI BOG (Ef 13-13)",  # Blagoslovljen budi Bog - Ef 1,3-14

        # Psalm-based matches continued
        "029": "BLAGOSLIVLJAJ DUŠO MOJA JAHVU - Ps 102 (103)",  # Blagoslovi dušo moju, Jahve - Psalam 103
        "030": "BENEDICTUS (Lk 1 68 - 79)",  # Benedictus - Zaharijina pjesma - Luka 1:68-79
        "031": "BLAGOSLIVLJAT ĆU GOSPODINA - Ps 33 (34)",  # Blagoslivljat ću Gospodina u svako doba - Ps 34
        "032": "BLAGOSLIVLJAJTE GOSPODINA - Ps 133 (134)",  # Blagoslivljajte Gospodina - Ps 134
        "033": "BLAGOSLOV VODE KRSNOG STUDENCA",  # Blagoslov vode krsnog zdenca
        "034": "BLAGOSLOV ZA POKORNIČKO SLAVLJE",  # Blagoslov za pokorničko slavlje
        "036": "BILA SU DVA ANĐELA",  # Bila dva anđela
        "037": "PJESMA TROJICE MLADIĆA (Dn 352 - 57)",  # Pjesma o troje mladih u peći – I dio - Dan 3:52-57
        "038": "PJESMA TROJICE MLADIĆA (Dn 3 57 - 88)",  # Pjesma o troje mladih u peći – II dio - Dan 3:57-88
        "039": "MOJSIJEVA PJESMA (Izl 15 1 - 18)",  # Mojsijeva pjesma – Pao je u more - Izlazak 15:1-18
        "041": "PJESMA OSLOBOĐENIKA (Iz 12 4 - 6)",  # Pjesma oslobođenika - Je 12,4-6
        "042": "JOŠUINA PJESMA (Jš 242-13)",  # Pjesma o Jošui - Jošu 24:2-18
        "043": "CARITAS CHRISTI (2 Kor 5 14 - 17. 21 1 Kor 9 16b) ()",  # Caritas Christi - 2 Kor 5,14ss
        "044": "CARMEN 63 (od Tagore)",  # Carmen '63 - poeziju R. Tagorea
        "047": "TKO ĆE NAS RASTAVITI (Rim 8 33 - 39)",  # Tko će nas rastaviti? - Rim 8,34-39
        "051": "KAKO JE LIJEPO KAKO RADUJE - Ps 132 (133)",  # Kako je lijep, kako daje radost - Ps 133
        "052": "KAO JELEN ČEZNE - Ps 41 - 42 (42 - 43)",  # Kao jelen čezne - Ps 42-43
        "056": "UTJEŠI MOJ NARODE (Iz 40 1 - 11)",  # Utješi moj narod - Izaija 40:1-11
        "057": "OVAKO GOVORI AMEN (Otk 3 14 - 20)",  # Ovako govori Amen - Otk 3,14-20
        "058": "APOSTOLSKO VJEROVANJE ()",  # Apostolsko vjerovanje

        # More complex matches based on content understanding
        "152": "NE OPIRITE SE ZLU (Mt 5 38 ss)",  # Ne opirite se zlu - Mt 5,38ss
        "155": "O BOŽE PO SVOJEM IMENU - Ps 53 (54)",  # Bože, sačuvaj me za svoje ime - Ps 54
        "156": "O BOŽE TI SI BOG MOJ - Ps 62 (63)",  # O Bože, ti si moj Bog - Psalam 63
        "157": "O ISUSE LJUBAVI MOJA",  # O Isuse, ljubavi moja
        "159": "O GOSPODINE BOG NAŠ - Ps 8",  # O Gospodine, Bože naš - Ps 8
        "160": "OČE NAŠ (Mt. 6 9-13) ()",  # Oče naš
        "231": "DOĐI S LIBANA (Pj 4 8 ss)",  # Vieni dal Libano

        # More matches from 59-88
        "059": "KRIST JE SVJETLOST (Iv 14 6)",  # Krist je svjetlo - Ivan 14:6
        "060": "IZ DUBINE SMRTI",  # Iz dubine smrti
        "061": "DAJENU",  # Dajenù - Pesach Haggadah
        "062": "IZ DUBINE VAPIJEM TEBI GOSPODINE - Ps 129 (130)",  # Iz dubine vapijem k Tebi - Ps 130
        "063": "PRED ANĐELIMA - Ps 137 (138)",  # Pred anđelima - Ps 138
        "064": "DEBORA (Suci 5)",  # Deborah - Suci 5
        "065": "DOSTOJAN SI (Otk 5 9 - 10)",  # Ti si vrijedan - Otk 5,9-10
        "066": "KAŽE GOSPODIN MOJEM GOSPODINU - Ps 109 (110)",  # Kaže Gospodin mom Gospodinu - Ps 110
        "067": "RECITE BOJAŽLJIVIMA (Iz 35)",  # Reci onima koji su srca bojažljivi - Je 35
        "068": "GDJE SI SE SAKRIO VOLJENI",  # Gdje si se sakrio, voljeni? - Duhovna pjesma
        "069": "UZAŠAO JE DOBRI PASTIR",  # Dobri pastir je uzašao
        "070": "STRPLJIV JE - HIMAN DUHU SVETOM",  # Strpljiv je - Hvalospjev Duhu Svetome
        "071": "EVO NAŠEG OGLEDALA (Oda XIII)",  # Ovdje je naše ogledalo - Oda XIII Salomona
        "072": "EVO SLUGE MOGA (Iz 42 1 - 4)",  # Evo sluge moga - Je 42,1-4
        "073": "EVO ME JA BRZO DOLAZIM (Otk 22 12 - 16)",  # Evo, dolazim brzo - Otk 22,12ss
        "074": "ELI ELI LAMA SABAKTANI - Ps 21 (22)",  # Eli, Eli, lamà sabachtani? - Ps 22
        "075": "USKLIKNITE PRAVEDNICI U GOSPODINU - Ps 32",  # Radujte se u Gospodinu, pravednici - Psalam 33
        "076": "HEVENU SHALOM ALEHEM (Hebrejska pjesma)",  # Evenu shalom alejem - židovska melodija
        "077": "BLAŽEN ČOVJEK - Ps 1",  # Sretan je čovjek - Psalam 1
        "078": "SREĆA ZA ČOVJEKA - Ps 127 (128)",  # Sreća za čovjeka - Ps 128
        "079": "KĆERI JERUZALEMSKE (Lk 23 28 - 46)",  # Kćeri jeruzalemske - Luka 23,28-46
        "080": "DOKLE ĆEŠ ME - Ps 12 (13)",  # Koliko dugo - Ps 13
        "081": "BRAĆO NE DAJMO NIKOME RAZLOG SPOTICANJA (Usp. 2 Kor 6 3 - 16)",  # Braćo, ne dajmo nikome kamen spoticanja - 2 Kor 6,3-16
        "082": "BJEŽI VOLJENI MOJ (Pj 8 10 - 14)",  # Bježi, voljeni moj - Pjesma nad pjesmama 8:10-14
        "083": "JERUZALEM PONOVNO IZGRAĐEN (Tob 13 11 - 18)",  # Jeruzalem ponovno izgrađen - Tobit 13:11-18
        "084": "ISUS JE PROŠAO KROZ SVE GRADOVE (Mt 9 35 ss)",  # Isus je prošao kroz sve gradove - Mt 9,35ss
        "085": "VEĆ DOLAZI MOJ BOG",  # Moj Bog dolazi - Božićna pjesma
        "086": "VEĆ DOLAZI KRALJEVSTVO (Otk 19 6 - 9)",  # Kraljevstvo sada dolazi - Otk 19,6-9
        "087": "JAKOV (Post 32 23 - 29)",  # Jakov - Post 32,23-29
        "088": "DAN ODMORA (Iv 8 51 56)",  # Dan odmora - Ivan 8:51,56

        # More matches from 89-118
        "089": "NEK DOPRE DO TEBE MOJA MOLITVA - Ps 118 (119)",  # Neka molitva moja dođe k Tebi - Ps 119
        "090": "NA RIJEKAMA BABILONIJE - Ps 136 (137)",  # Stigao do rijeka Babilona - Ps 137
        "091": "SLAVA BOGU NA VISINI",  # Slava Bogu na visini
        "092": "HVALITE JAHVU - Ps 135 (136)",  # Hvala Jahvi - Ps 136
        "093": "KLIČITE OD RADOSTI (Iz 12 1 ss)",  # Kličite od radosti - Iz 12,1ss
        "094": "GLEDAJTE KAKO JE DOBRO - Ps 132 (133)",  # Pogledaj kako je lijepa - Ps 133
        "095": "GLE KAKO JE DOBRA - Ps 132 (133)",  # Vidi kako je lijepo, kušaj kako je slatko - Ps 133
        "096": "KUŠAJTE I VIDITE - Ps 33 (34)",  # Kušajte i vidite - Ps 34
        "097": "UZDAH SE UZDAH SE U GOSPODINA - Ps 39 (40)",  # Nadao sam se, nadao sam se u Gospodina - Ps 40
        "098": "ISPRUŽIO SAM RUKE (Oda XXVII)",  # Ispružio sam ruke - oda XXVII Salomona
        "099": "MESIJA LAV ZA POBJEDU",  # Mesija, lav za pobjedu
        "100": "TIJESNIK (Iz 63 1 - 6)",  # Riznica - Izaija 63:1-6
        "101": "NAROD KOJI JE U TMINI HODIO (Iz 9 1 - 5)",  # Ljudi koji su hodali u tami - Je 9,1-5
        "102": "SIJAČ (Mk 4 3 - 9)",  # Sijač - Mk 4,3-9
        "103": "GOSPODIN NAJAVLJUJE VIJEST - Ps 67 (68)",  # Gospodin najavljuje vijest - Ps 68
        "104": "GOSPODIN JE PASTIR MOJ - Ps 22 (23)",  # Gospodin je pastir moj - Psalam 23
        "105": "GOSPODIN MI JE SVJETLOST I SPASENJE - Ps 26 (27)",  # Gospodin je moje svjetlo i moje spasenje - Psalam 27
        "106": "GOSPODIN MI JE DAO (Iz 50 4 - 11)",  # Gospodin mi je dao - Iz 50,4-11
        "107": "USRED JEDNOG VELIKOG MNOŠTVA",  # Usred velikog mnoštva - Luka 8:42-48
        "108": "U TAMNOJ NOĆI",  # U tamnoj noći - sv. Ivan od Križa
        "109": "HIMAN KRISTU SVJETLOSTI",  # Hvalospjev Kristu svjetlu - sv. Grgur Nazijanski
        "110": "HIMAN LJUBAVI (1 Kor 13 1 - 7)",  # Hvalospjev milosrđu - 1 Kor 13,1-7
        "111": "HIMAN SLAVNOM KRIŽU",  # Himna slavnom križu
        "112": "ISUS KRIST JE GOSPODIN (Fil 2 1 - 11)",  # Himna Kenozi – Krist Isus je Gospodin - Fil 2,1-11
        "113": "ADVENTSKI HIMAN",  # Adventski hvalospjev
        "114": "USKRSNI HIMAN",  # Uskrsna pjesma
        "115": "DOLAZIM SKUPITI (Iz 66 18 - 23)",  # Dolazim skupiti - Je 66,18-23
        "116": "JAHVE TI SI MOJ BOG (Iz 25 1 - 8)",  # Jahve, ti si moj Bog - Je 25,1-8
        "117": "GOLUB JE POLETIO (Oda XXIV)",  # Golub je poletio - oda XXIV Salomona
        "118": "MAČ (Ez 21 14 - 22)",  # Mač - Ez 21,14-22

        # More matches from 119-148
        "119": "TVRD JE HOD",  # Hod je težak - "Go Down Moses"
        "120": "MOJ VOLJENI JE MOJ (Pj 1 13 - 16)",  # Moj voljeni je moj - Pjesme 1,13-16
        "121": "ŽETVA NARODA (Iv 4 31 - 38)",  # Žetva naroda - Ivan 4:31-38
        "122": "ZDRAVO KRALJICE NEBESKA",  # Zdravo - Zdravo Sveta Kraljice
        "123": "GLAS MOGA VOLJENOG (Pj 2 8 - 17)",  # Glas moga voljenog - Pjesma nad pjesmama 2:8-17
        "124": "OBAVILI SU ME VALOVI SMRTI - Ps 17 (18)",  # Obavili su me valovi smrti - Ps 18
        "125": "NJEGOVI TEMELJI - Ps 86 (87)",  # Njegovi temelji - Ps 87
        "126": "LITANIJE SVIH SVETIH",  # Litanije za svete
        "127": "POKORNIČKE LITANIJE KRATKE",  # Pokorničke litanije I
        "128": "POKORNIČKE LITANIJE",  # Pokorničke litanije II
        "129": "DUH JE GOSPODNJI NA MENI (Lk 4 18 - 19)",  # Duh je Gospodnji na meni - Luka 4:18-19
        "130": "SAM BOG (2 Kor 4 6 - 12)",  # Sam Bog - 2 Kor 4,6-12
        "131": "BEZUMNIK MISLI DA NEMA BOGA - Ps 13 (14)",  # Budala misli da nema Boga - Ps 14
        "132": "HVALITE BOGA ALELUJA - Ps 150",  # Slava Bogu - Psalam 150
        "133": "HVALITE GOSPODINA S NEBESA - Ps 148 ()",  # Hvalite Gospodina s nebesa - Ps 148
        "134": "HVALITE GOSPODINA SVI NARODI ZEMLJE - Ps 116 (117)",  # Hvalite Gospodina svi narodi zemlje - Ps 117
        "135": "MAGNIFICAT (Lk 1 46 - 55)",  # Magnificat - Pjesma Veliča - Lk 1,46-55
        "136": "MARIA DI JASNA GORA ()",  # Marija od Jasne Gore - Himna Gospi od Częstochowa
        "137": "MARIJO KUĆO BLAGOSLOVA",  # Marija, kuća blagoslova - Iv 2,1-10
        "138": "MARIJO MAJKO GORUĆEG PUTA",  # Marija, Majka žarkog puta
        "139": "MARIJA MAJKA CRKVE (Iv 1926-34)",  # Marija, majka Crkve - Iv 19,26-34
        "140": "MARIJO MALA MARIJO",  # Marijo, mala Marijo - Himna Djevici Mariji
        "141": "MELODIJA ZA SVEOPĆU MOLITVU",  # Melodija za sveopću molitvu
        "142": "ZAVEO SI ME GOSPODINE (Jer 20 7 - 18)",  # Zaveo si me, Gospodine - Jer 20,7-18
        "143": "POKAZAT ĆEŠ MI STAZU ŽIVOTA - Ps 15 (16)",  # Ti ćeš mi pokazati stazu života - Ps 16
        "144": "UKRAO SI MI SRCE (Pj 4 9 - 5 1)",  # Ukrao si mi srce - Pjesma nad pjesmama 4:9-5:1
        "145": "SMILUJ MI SE BOŽE - Ps 50 (51)",  # Milost, Bože, milost - Ps 51
        "146": "MNOGO SU ME PROGANJALI - Ps 128",  # Mnogo su me progonili - Ps 129
        "147": "NITKO NE MOŽE SLUŽITI DVOJICI GOSPODARA (Mt 6 24 - 33)",  # Nitko ne može služiti dvojici gospodara - Mt 6,24-33
        "148": "NOLI ME TANGERE (Iv 20 15 - 17)",  # Noli me tangere - Ivan 20,15-17

        # More matches from 149-178
        "149": "NEMA U NJEMU LJEPOTE (Iz 53 2 - 7)",  # Nema u njemu ljepote - Je 53,2-7
        "150": "NIJE OVDJE (Mt 28 1 - 7) ()",  # On nije ovdje. On je uskrsnuo! - Mt 28,1-7
        "151": "NEĆU UMRIJETI - Ps 117 (118) ()",  # Neću umrijeti - Ps 118
        "153": "NE LJUTI SE - Ps 36 (37)",  # Ne ljuti se - Ps 37
        "154": "NEBESA KIŠITE ODOZGO (Iz 458)",  # O nebesa, kiša odozgor - Is 45,8
        "158": "O SMRTI GDJE JE TVOJA POBJEDA (1 Kor 15)",  # O smrti, gdje je tvoja pobjeda? - 1 Kor 15
        "161": "PEDESETNICA (Dj 2 1 - 13)",  # Pedesetnica - Dj 2,1-13
        "162": "IZ LJUBAVI PREMA BRAĆI SVOJOJ - PS 121 (122)",  # Za ljubav moje braće - Ps 122
        "163": "ZAŠTO SE NARODI ROTE - Ps 2",  # Zašto se narodi urote? - Ps 2
        "164": "MILOSRĐE BOŽE - Ps 50 (51)",  # Smiluj mi se, Bože - Psalam 51
        "165": "PRIJEKORI GOSPODINOVI - PUČE MOJ",  # Ljudi moji - "Improperia"
        "166": "UZMI ME U NEBO (Fil 1 23)",  # Uzmi me u nebo - Fil 1:23
        "167": "PASHALNI HVALOSPJEV",  # Pashalno proročanstvo - Exultet
        "168": "HIMAN POHVALA DOŠAŠĆA DO 16. PROSINCA",  # Predslovlje došašća
        "169": "PASHALNO PREDSLOVLJE",  # Uskrsno predslovlje I
        "170": "DRUGA EUHARISTIJSKA MOLITVA",  # Euharistijska molitva II - Model 1
        "171": "DRUGA EUHARISTIJSKA MOLITVA (2) Predslovlje",  # Euharistijska molitva II - Model 2
        "172": "ČETVRTA EUHARISTIJSKA MOLITVA",  # Euharistijska molitva IV
        "173": "DIĆI ĆU ČAŠU SPASENJA - Ps 114 - 115 (116)",  # Uzet ću i podići čašu spasenja - Ps 116
        "174": "KAD SAM SPAVAO (Pj 5 2 4 - 8)",  # Kad sam spavao - Pjesma nad pjesmama 5:2,4-8
        "175": "KADA GOSPODIN - Ps 125 (126)",  # Kad Gospodin - Ps 126
        "176": "KADA IZRAEL IZAÐE IZ EGIPTA - Ps 113 A (114)",  # Kad je Izrael izašao iz Egipta - Ps 114
        "177": "KAKO SU MILI STANOVI TVOJI - Ps 83 (84)",  # Kako su lijepa vaša prebivališta - Ps 84
        "178": "OVO JE MOJA ZAPOVIJED (Iv 15 12 ss)",  # Ovo je moja zapovijed - Ivan 15:12ss

        # More matches from 179-208
        "179": "USKRSNUĆE (Iv 11 25 - 27)",  # Uskrsnuće - Ivan 11,25-27
        "180": "ODGOVORI NA MOLITVE",  # Odgovori na dove
        "181": "USKRSNUO JE (usp. 1 Kor 15)",  # On je uskrsnuo - 1 Kor 15,54-58
        "182": "OBUCITE SE U BOJNU OPREMU BOŽJU (Ef 6 11 - 17)",  # Obucite oružje Božje - Ef 6,11-17
        "183": "PJEVANA KRUNICA",  # Pjevana krunica
        "184": "BOG SE DIŽE S HVALOSPJEVOM - Ps 46 (47)",  # Bog ustaje usred klicanja - Ps 47
        "185": "NEK SE ZARUČNIK POPNE NA DRVO (Himan sv. Quodvultdeusa)",  # Neka se zaručnik popne na drvo
        "186": "PSALMODIJA ZA RESPONZORIJSKI PSALAM",  # Psalmodij za responzorijski psalam
        "187": "PSALMODIJE ZA POHVALE",  # Psalmodije za pohvale
        "188": "ZDRAVO KRALJICE NEBESKA",  # Zdravo, Kraljice neba - marijska antifona
        "189": "SVET (1983.)",  # Svetac - 1982
        "190": "SVET SVET SVET (1988.)",  # Sveti – Rim 1977
        "191": "SVET JE SVET (Korizmeno vrijeme)",  # Svetac koliba
        "192": "SVET JE GOSPODIN - SVET BARAKA (U vrijeme Došašća)",  # Svetac od palmi
        "193": "SVET SVET SVET - HOSANA CVJETNICE (i u pashalno vrijeme)",  # Sveto je sveto - Židovska melodija
        "194": "SVET SVET SVET (1988.)",  # Svet, Svet, Svet - 1988
        "195": "AKO GOSPODIN KUĆE NE GRADI - Ps 126 (127)",  # Ako Gospodin ne sagradi kuću - Ps 127
        "196": "AKO SE GOSPODINU JA UTEKOH - Ps 10 (11)",  # Ako sam se utekao Gospodinu - Ps 11
        "197": "AKO DANAS ČUJETE NJEGOV GLAS - Ps 94 (95)",  # Ako danas slušaš njegov glas - Ps 95
        "198": "AKO STE USKRSNULI S KRISTOM",  # Ako ste uskrsnuli s Kristom - Kol 3,1-4
        "199": "TIJELOVSKA SEKVENCA",  # Tijelovska sekvenca - sv. Toma Akvinski
        "200": "DUHOVSKA POSLJEDNICA (DOĐI DUŠE SVETI)",  # Slijed Pedesetnice – Dođi, Duše Sveti
        "201": "PROPOVIJED NA GORI (Lk 6 20 - 30)",  # Propovijed na gori - Luka 6:20-30.37
        "202": "SHEMA ISRAEL (Pnz 6 4 - 9)",  # Shema Israel - Dt 6,4-9
        "203": "SHLOM LECH MARIAM",  # Shlom Lech Marìam - Ave Maria na aramejskom
        "204": "SJEDNI OSAMLJEN I ŠUTLJIV (Tuž 3 1 - 33)",  # Sjedi sam i šuti - Lam 3,1-33
        "205": "GOSPODINE POMOZI MI",  # Gospodine, pomozi mi, Gospodine
        "206": "GOSPODINE MOJE SRCE VIŠE NEMA ZAHTJEVA - Ps 130 (131)",  # Gospodine, moje srce nema više pretenzija - Ps 131
        "207": "GOSPODINE NEMOJ ME KAZNITI - Ps 6",  # Gospodine, ne kazni me u svom gnjevu - Ps 6
        "208": "GOSPODINE TI ME PRONIČEŠ I TI ME POZNAJEŠ - Ps 138 (139)",  # Gospodine, ti me ispituj i upoznaj - Ps 139

        # Final matches from 209-238
        "209": "SAMA SA SAMIM",  # Sam sam
        "210": "BOG NEK USTANE - Ps 67 (68) (rr 2. 4 - 7)",  # Neka ustane Bog - Psalam 68
        "211": "STABAT MATER",  # Stabat Mater Dolorosa
        "212": "TE DEUM",  # Te Deum
        "213": "TEBI SAM OBJAVIO SVOJ GRIJEH - Ps 31 (32)",  # Otkrio sam ti svoj grijeh - Ps 32
        "214": "PRIZIVLJEM TE - Ps 140 (141)",  # Zovem te - Ps 141
        "215": "VIDJET ĆE TE KRALJEVI II. PJESMA O SLUZI (Iz 49 1 - 16)",  # Kraljevi će te vidjeti - Iz 49,1-16
        "216": "TI KOJI SI VJERAN - Ps 142 (143)",  # Ti koji si vjeran - Ps 143
        "217": "POKRIO SI SMRT SRAMOTOM (Meliton iz Sarda)",  # Pokrio si smrt sramotom - Meliton iz Sarda
        "218": "LIJEPA SI PRIJATELJICE MOJA (Pj 6 - 7)",  # Lijepa si, prijateljice - Pjesma nad pjesmama 6;7
        "219": "TI SI NAJLJEPŠI - Ps 44 (45)",  # Ti si najljepša - Ps 45
        "220": "TI SI MOJA NADA GOSPODINE (XXIX. Salomonova oda)",  # Ti si moja nada, Gospodine - Solomonova oda XXIX
        "221": "JEDNA MLADICA KLIJA IZ PANJA JIŠAJEVA (Iz 11)",  # Izdanak izlazi iz Jišajeva panja - Je 11,1-11a
        "222": "VELIČANSTVEN ZNAK (Otk 12)",  # Žena obučena u sunce - Otk 12
        "223": "URI URI URA",  # Uri, Uri, Uri - Božićna pjesma
        "224": "PJEVANO EVANĐELJE (Lk 22 28 - 34)",  # Pjevano evanđelje - Lk 22,28-34
        "225": "VIDIM NEBESA OTVORENA (Otk 19 11 - 20)",  # Vidim nebesa otvorena - Otk 19,11-20
        "226": "DOĐITE K MENI SVI VI (Mt 11 28 - 30)",  # Dođite svi k meni - Mt 11,28-30
        "227": "DJEVICA DIVOTE",  # Virgin of Wonder - Dante Alighieri
        "228": "PREMA TEBI GRADE SVETI",  # Prema tebi, o sveti grade
        "229": "UZET ĆU VAS IZ NARODA (Ez 36 24 - 28)",  # Ja ću te uzeti iz naroda - Ez 36,24-28
        "230": "DOLAZI GOSPODIN U SLAVU ZAODJEVEN",  # Gospodin dolazi, obučen u veličanstvo - Ps 93, Otk 1,5-7
        "232": "DOĐI SINE ČOVJEČJI (Otk 22 17)",  # Dođi, sine čovječji - Otk 22,17ss
        "233": "DUHOVSKI HIMAN O DOĐI STVORČE DUŠE SVET",  # Dođi, Duše Stvoritelju
        "234": "ŽIVITE RADOSNO (Fil 4 4 ss)",  # Živite radosno - Fil 4,4ss
        "235": "ŽELIM POĆI U JERUZALEM (Sefarditska pjesma)",  # Želim ići u Jeruzalem - Sefardsko pjevanje
        "236": "JA HOĆU PJEVATI - Ps 56 (57)",  # Želim pjevati - Psalam 57
        "237": "VI STE SVJETLO SVIJETA (Mt 5 14 - 16)",  # Vi ste svjetlo svijeta - Mt 5,14-16
        "238": "ZAKEJ (Lk. 19 1 - 10)",  # Zakej - Lk 19,1-10
    }

    return manual_matches

def main():
    print("🎯 Manual Song Matching using LLM Understanding")
    print("=" * 60)
    
    # Load data
    translation_data = parse_translation_file('LISTA-IT-GOOGLE-HR.md')
    croatian_songs = get_parsed_croatian_songs('lang/hr/04_chordpro')
    
    print(f"📚 Loaded {len(translation_data)} Italian songs")
    print(f"🎵 Found {len(croatian_songs)} Croatian songs")
    
    # Get manual matches (concepts)
    manual_match_concepts = create_manual_matches()

    # Multi-pass matching system
    actual_matches = {}
    used_croatian_songs = set()

    # PASS 1: Biblical reference matching with semantic verification
    print("🎯 Pass 1: Biblical reference matching with semantic verification...")
    for italian_data in translation_data:
        italian_id = italian_data['id']
        italian_ref = extract_biblical_reference(italian_data['italian'])

        if italian_ref:
            italian_ref_norm = normalize_biblical_reference(italian_ref)

            # Find ALL Croatian songs with matching biblical reference
            biblical_candidates = []

            for croatian_song in croatian_songs:
                if croatian_song in used_croatian_songs:
                    continue

                croatian_ref = extract_biblical_reference(croatian_song)
                if croatian_ref:
                    croatian_ref_norm = normalize_biblical_reference(croatian_ref)

                    # Check for exact normalized match
                    if italian_ref_norm == croatian_ref_norm and italian_ref_norm:
                        biblical_candidates.append(croatian_song)

                    # Check for Ode matches (XL. Salomonova oda ↔ Ode XL)
                    elif 'oda' in croatian_ref.lower() and 'ode' in italian_ref.lower():
                        # Extract Roman numerals
                        italian_num = re.search(r'[IVX]+', italian_ref)
                        croatian_num = re.search(r'[IVX]+', croatian_ref)
                        if italian_num and croatian_num and italian_num.group() == croatian_num.group():
                            biblical_candidates.append(croatian_song)

            # Now choose the best candidate using semantic similarity
            if biblical_candidates:
                best_candidate = None
                best_score = 0.0

                for candidate in biblical_candidates:
                    semantic_score = calculate_similarity(italian_data, candidate)
                    if semantic_score > best_score:
                        best_score = semantic_score
                        best_candidate = candidate

                # Accept the match if it passes semantic verification (40% threshold)
                if best_candidate and best_score >= 0.4:
                    actual_matches[italian_id] = best_candidate
                    used_croatian_songs.add(best_candidate)
                    match_type = "📜 Ode" if 'oda' in extract_biblical_reference(best_candidate).lower() else "📖 Biblical"
                    print(f"   {match_type} match: {italian_id} - {italian_ref} ↔ {extract_biblical_reference(best_candidate)} (semantic: {best_score:.3f})")
                elif biblical_candidates:
                    print(f"   ❌ Biblical match rejected: {italian_id} - {italian_ref} (semantic too low: {best_score:.3f})")

    # PASS 2: Psalm number matching (switched numbering)
    print("🎯 Pass 2: Psalm number matching...")
    for italian_data in translation_data:
        italian_id = italian_data['id']
        if actual_matches.get(italian_id):  # Skip if already matched
            continue

        italian_ref = extract_biblical_reference(italian_data['italian'])
        italian_num1, italian_num2 = extract_psalm_numbers(italian_ref)

        if italian_num1:
            for croatian_song in croatian_songs:
                if croatian_song in used_croatian_songs:
                    continue

                croatian_ref = extract_biblical_reference(croatian_song)
                croatian_num1, croatian_num2 = extract_psalm_numbers(croatian_ref)

                if croatian_num1:
                    # Italian: Vulgate (Jerusalem), Croatian: Jerusalem (Vulgate)
                    # Perfect match: Italian first = Croatian second, Italian second = Croatian first
                    if italian_num2 and croatian_num2:
                        if italian_num1 == croatian_num2 and italian_num2 == croatian_num1:
                            actual_matches[italian_id] = croatian_song
                            used_croatian_songs.add(croatian_song)
                            break
                    # Simple match: same psalm number
                    elif italian_num1 == croatian_num1:
                        actual_matches[italian_id] = croatian_song
                        used_croatian_songs.add(croatian_song)
                        break

    # PASS 3: High-confidence semantic matches (70% threshold)
    print("🎯 Pass 3: High-confidence semantic matching (70%)...")
    for italian_data in translation_data:
        italian_id = italian_data['id']
        if actual_matches.get(italian_id):  # Skip if already matched
            continue

        best_match = None
        best_score = 0.0

        for croatian_song in croatian_songs:
            if croatian_song in used_croatian_songs:
                continue

            score = calculate_similarity(italian_data, croatian_song)
            if score > best_score and score >= 0.7:  # High threshold
                best_score = score
                best_match = croatian_song

        if best_match:
            actual_matches[italian_id] = best_match
            used_croatian_songs.add(best_match)

    # PASS 4: Medium-confidence semantic matches (50% threshold)
    print("🎯 Pass 4: Medium-confidence semantic matching (50%)...")
    for italian_data in translation_data:
        italian_id = italian_data['id']
        if actual_matches.get(italian_id):  # Skip if already matched
            continue

        best_match = None
        best_score = 0.0

        for croatian_song in croatian_songs:
            if croatian_song in used_croatian_songs:
                continue

            score = calculate_similarity(italian_data, croatian_song)
            if score > best_score and score >= 0.5:  # Medium threshold
                best_score = score
                best_match = croatian_song

        if best_match:
            actual_matches[italian_id] = best_match
            used_croatian_songs.add(best_match)

    # PASS 5: Manual concept matches (from our predefined list)
    print("🎯 Pass 5: Manual concept matching...")
    for italian_id, croatian_concept in manual_match_concepts.items():
        if actual_matches.get(italian_id) or not croatian_concept:  # Skip if already matched or no concept
            continue

        # Try to find exact match first
        for croatian_song in croatian_songs:
            if croatian_song in used_croatian_songs:
                continue
            if croatian_song == croatian_concept:
                actual_matches[italian_id] = croatian_song
                used_croatian_songs.add(croatian_song)
                break

        # If no exact match, try similarity
        if not actual_matches.get(italian_id):
            best_match = None
            best_score = 0.0

            for croatian_song in croatian_songs:
                if croatian_song in used_croatian_songs:
                    continue

                score = similarity(croatian_concept, croatian_song)
                if score > best_score and score >= 0.6:  # Lower threshold for manual concepts
                    best_score = score
                    best_match = croatian_song

            if best_match:
                actual_matches[italian_id] = best_match
                used_croatian_songs.add(best_match)

    # Create output
    output_file = 'manual_song_matches.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Manual Song Matches (LLM-based)\n\n")
        f.write("| Italian ID | Italian Title | Croatian Title |\n")
        f.write("|----|----|----|\\n")

        for song_data in translation_data:
            italian_id = song_data['id']
            italian_full = song_data['italian']

            # Extract just the title (remove ID and reference)
            italian_title = extract_italian_title(italian_full)

            # Get the actual Croatian match
            croatian_match = actual_matches.get(italian_id, "")
            # Clean the Croatian title (remove references)
            croatian_clean = clean_croatian_title(croatian_match)

            f.write(f"| {italian_id} | {italian_title} | {croatian_clean} |\n")

        # Write results to file
        for song_data in translation_data:
            italian_id = song_data['id']
            italian_full = song_data['italian']

            # Extract just the title (remove ID and reference)
            italian_title = extract_italian_title(italian_full)

            # Get the actual Croatian match
            croatian_match = actual_matches.get(italian_id, "")
            # Clean the Croatian title (remove references)
            croatian_clean = clean_croatian_title(croatian_match)

            f.write(f"| {italian_id} | {italian_title} | {croatian_clean} |\n")

        # Find truly unmatched Croatian songs
        unmatched_croatian = [song for song in croatian_songs if song not in used_croatian_songs]

        if unmatched_croatian:
            f.write("\n## Unmatched Croatian Songs\n\n")
            f.write("| Croatian Title |\n")
            f.write("|----|\n")
            for song in sorted(unmatched_croatian):
                f.write(f"| {song} |\n")

    print(f"✅ Created {output_file} with multi-pass matching")
    print(f"🎵 Total Croatian matches found: {len([m for m in actual_matches.values() if m])}")
    print(f"📝 Remaining unmatched Croatian songs: {len(unmatched_croatian)}")

    # Show pass-by-pass statistics
    pass1_matches = sum(1 for i, song_data in enumerate(translation_data) if actual_matches.get(song_data['id']) and i < 50)  # Rough estimate
    print(f"📊 Multi-pass matching results:")
    print(f"   🎯 Biblical references + Psalms: High-confidence matches")
    print(f"   📈 Semantic 70%: High-confidence semantic matches")
    print(f"   📈 Semantic 50%: Medium-confidence semantic matches")
    print(f"   📝 Manual concepts: Predefined concept matches")

    if len(unmatched_croatian) > 0:
        print(f"⚠️  Note: {len(unmatched_croatian)} Croatian songs still unmatched - consider manual review")

if __name__ == "__main__":
    main()
