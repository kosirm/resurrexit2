#!/usr/bin/env python3
"""
Script to match Croatian songs with Italian song IDs using translation and biblical references
"""

import re
import os
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional

def extract_biblical_reference(text: str) -> Optional[str]:
    """Extract biblical references like 'Ps 123 (122)', 'Mt 28,7-10', etc."""
    # Common patterns for biblical references
    patterns = [
        r'Ps\s*\d+\s*\(\d+\)',  # Ps 123 (122)
        r'Psalam\s*\d+\s*\(\d+\)',  # Psalam 123 (122)
        r'Mt\s*\d+[,\d\-]*',  # Mt 28,7-10
        r'Lk\s*\d+[,\d\-]*',  # Lk 1,42-45
        r'Luka\s*\d+[:\d\-]*',  # Luka 1:42-45
        r'Rm\s*\d+[,\d\-]*',  # Rm 8,15-17
        r'Rim\s*\d+[,\d\-]*',  # Rim 8,34-39
        r'Dn\s*\d+[,\d\-]*',  # Dn 3,52-57
        r'Dan\s*\d+[:\d\-]*',  # Dan 3:52-57
        r'Izl\s*\d+[,\d\-]*',  # Izl 15,1-2
        r'Izlazak\s*\d+[:\d\-]*',  # Izlazak 15:1-18
        r'Post\s*\d+[,\d\-]*',  # Post 18,1-5
        r'Ef\s*\d+[,\d\-]*',  # Ef 1,3-14
        r'Otk\s*\d+[,\d\-]*',  # Otk 7,12-14
        r'Jš\s*\d+[,\d\-]*',  # Jš 24,2-13
        r'Jošu\s*\d+[:\d\-]*',  # Jošu 24:2-18
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group().strip()
    return None

def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (0.0 to 1.0)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_title(title: str) -> str:
    """Normalize title for better matching"""
    # Remove common prefixes/suffixes and normalize
    title = re.sub(r'^\d+\s*-\s*', '', title)  # Remove number prefix
    title = re.sub(r'\s*-\s*Cfr\..*$', '', title)  # Remove biblical reference
    title = re.sub(r'\s*-\s*Vidi.*$', '', title)  # Remove "Vidi" reference
    title = re.sub(r'\s*\([^)]*\)$', '', title)  # Remove parentheses at end
    return title.strip().upper()

def parse_translation_file(filepath: str) -> List[Dict]:
    """Parse the LISTA-IT-GOOGLE-HR.md file"""
    songs = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Skip header lines
    for line in lines[2:]:  # Skip header and separator
        line = line.strip()
        if not line or line.startswith('|---'):
            continue
            
        # Split by | and clean up
        parts = [part.strip() for part in line.split('|')[1:-1]]  # Remove empty first/last
        if len(parts) >= 3:
            italian = parts[0].strip()
            google_translate = parts[1].strip()
            croatian = parts[2].strip()
            
            # Extract ID from Italian title
            id_match = re.match(r'^(\d+)', italian)
            song_id = id_match.group(1) if id_match else None
            
            if song_id:  # Include all Italian songs, even if Croatian column is empty
                songs.append({
                    'id': song_id,
                    'italian': italian,
                    'google_translate': google_translate,
                    'croatian': croatian,
                    'italian_biblical_ref': extract_biblical_reference(italian),
                    'google_biblical_ref': extract_biblical_reference(google_translate),
                    'italian_normalized': normalize_title(italian),
                    'google_normalized': normalize_title(google_translate),
                    'croatian_normalized': normalize_title(croatian)
                })
    
    return songs

def get_parsed_croatian_songs(chordpro_folder: str) -> List[str]:
    """Get list of Croatian song titles from parsed ChordPro files"""
    songs = []
    
    if not os.path.exists(chordpro_folder):
        print(f"❌ Folder not found: {chordpro_folder}")
        return songs
    
    for filename in os.listdir(chordpro_folder):
        if filename.endswith('.chordpro'):
            # Extract title from filename (remove number prefix and .chordpro)
            title = filename.replace('.chordpro', '')
            title = re.sub(r'^\d+-\d+-', '', title)  # Remove number prefix like "2-01-"
            title = re.sub(r'^\d+-', '', title)  # Remove simple number prefix
            songs.append(title.strip())
    
    return sorted(songs)

def extract_italian_parts(italian_text: str) -> Tuple[str, str]:
    """Extract title and reference from Italian song format: 'ID - title - reference'"""
    # Split by ' - ' and take parts after the ID
    parts = italian_text.split(' - ', 2)  # Split into max 3 parts
    if len(parts) >= 2:
        title = parts[1].strip()
        reference = parts[2].strip() if len(parts) >= 3 else ""
        return title, reference
    return "", ""

def extract_croatian_parts(croatian_text: str) -> Tuple[str, str]:
    """Extract title and reference from Croatian song format: 'title (reference)'"""
    # Find the last parentheses for reference
    match = re.match(r'^(.*?)\s*\(([^)]*)\)\s*$', croatian_text.strip())
    if match:
        title = match.group(1).strip()
        reference = match.group(2).strip()
        return title, reference
    else:
        # No parentheses, whole text is title
        return croatian_text.strip(), ""

def normalize_for_comparison(text: str) -> str:
    """Normalize text for better comparison"""
    # Remove common Croatian/Italian variations
    text = text.upper()
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation

    # Handle accented characters
    text = text.replace('À', 'A').replace('È', 'E').replace('Ì', 'I').replace('Ò', 'O').replace('Ù', 'U')
    text = text.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')

    # Common word mappings Croatian <-> Italian
    replacements = {
        'GOSPODINE': 'SIGNORE',
        'GOSPODIN': 'SIGNOR',
        'JAHVE': 'SIGNORE',
        'JAHVU': 'SIGNORE',
        'BOŽE': 'DIO',
        'BOG': 'DIO',
        'TEBI': 'TE',
        'MOJA': 'MIA',
        'MOJE': 'MIO',
        'DUŠU': 'ANIMA',
        'DUŠA': 'ANIMA',
        'SRCE': 'CUORE',
        'LJUBAV': 'AMORE',
        'HVALITE': 'LODATE',
        'SLAVITI': 'LODARE',
        'PJEVAJTE': 'CANTATE',
        'KLIČITE': 'GRIDATE',
        'RADUJTE': 'GIOITE',
        'VIENI': 'DODI',
        'VIENI': 'DODITE'
    }

    for croatian, italian in replacements.items():
        text = text.replace(croatian, italian)

    return text.strip()

def extract_psalm_numbers(ref: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract psalm numbers from biblical reference"""
    if not ref:
        return None, None

    # Look for pattern like "Sal 25 (24)" or "Ps 24 (25)"
    match = re.search(r'(?:Sal|Ps|Psalam)\s*(\d+)\s*\((\d+)\)', ref, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)

    # Look for simple pattern like "Ps 123"
    match = re.search(r'(?:Sal|Ps|Psalam)\s*(\d+)', ref, re.IGNORECASE)
    if match:
        return match.group(1), None

    return None, None

def find_matches(translation_data: List[Dict], parsed_songs: List[str]) -> List[Dict]:
    """Find matches: for each Italian song, find the best matching Croatian song"""
    matches = []
    used_croatian_songs = set()  # Track which Croatian songs are already matched

    # For each Italian song, find the best matching Croatian song
    for italian_song_data in translation_data:
        italian_id = italian_song_data['id']
        italian_title = italian_song_data['italian']
        google_translate = italian_song_data['google_translate']
        italian_biblical_ref = italian_song_data['italian_biblical_ref']

        best_croatian_match = None
        best_score = 0.0

        # Extract Italian title and reference
        italian_title, italian_ref = extract_italian_parts(italian_title)

        # Try to find the best Croatian match for this Italian song
        for croatian_song in parsed_songs:
            # Skip if this Croatian song is already matched
            if croatian_song in used_croatian_songs:
                continue

            # Extract Croatian title and reference
            croatian_title, croatian_ref = extract_croatian_parts(croatian_song)

            # Calculate different similarity scores
            scores = []

            # 1. Direct title comparison (most important)
            if italian_title and croatian_title:
                score_title = similarity(italian_title, croatian_title)
                scores.append(('title_direct', score_title))

            # 2. Normalized title comparison
            if italian_title and croatian_title:
                normalized_italian = normalize_for_comparison(italian_title)
                normalized_croatian = normalize_for_comparison(croatian_title)
                if normalized_italian and normalized_croatian:
                    score_normalized = similarity(normalized_italian, normalized_croatian)
                    scores.append(('title_normalized', score_normalized))

            # 3. Google translation fallback (for complex cases)
            if google_translate and croatian_song:
                score_google = similarity(google_translate, croatian_song)
                scores.append(('google_fallback', score_google * 0.7))  # Lower weight

            # 4. Single word exact match (for cases like AKEDA ↔ Akedà)
            if italian_title and croatian_title:
                # Clean and compare single words
                italian_clean = normalize_for_comparison(italian_title)
                croatian_clean = normalize_for_comparison(croatian_title)

                if italian_clean == croatian_clean:
                    scores.append(('exact_match', 1.0))
                elif len(italian_clean.split()) == 1 and len(croatian_clean.split()) == 1:
                    # Single word comparison with high similarity
                    single_word_score = similarity(italian_clean, croatian_clean)
                    if single_word_score > 0.7:
                        scores.append(('single_word', single_word_score))

            # Get the best score from all methods
            if scores:
                best_method, base_score = max(scores, key=lambda x: x[1])
            else:
                base_score = 0.0

            # Bonus for biblical reference matching (corrected for psalm numbering)
            bonus = 0.0
            croatian_ref = extract_biblical_reference(croatian_song)

            if italian_biblical_ref and croatian_ref:
                italian_num1, italian_num2 = extract_psalm_numbers(italian_biblical_ref)
                croatian_num1, croatian_num2 = extract_psalm_numbers(croatian_ref)

                if italian_num1 and croatian_num1:
                    # Italian: Vulgate (Jerusalem), Croatian: Jerusalem (Vulgate)
                    # So Italian first number should match Croatian second number
                    # And Italian second number should match Croatian first number
                    if italian_num2 and croatian_num2:
                        if italian_num1 == croatian_num2 and italian_num2 == croatian_num1:
                            bonus = 0.4  # Perfect psalm match with both numbering systems
                        elif italian_num1 == croatian_num1 or italian_num2 == croatian_num2:
                            bonus = 0.2  # Partial psalm match
                    elif italian_num1 == croatian_num1:
                        bonus = 0.3  # Simple psalm number match

            final_score = base_score + bonus

            if final_score > best_score:  # Remove threshold - accept any best match
                best_croatian_match = croatian_song
                best_score = final_score

        # Add the match (even if no Croatian song found - will show empty)
        matches.append({
            'italian_id': italian_id,
            'italian': italian_title,
            'google_translate': google_translate,
            'matched_parsed_song': best_croatian_match if best_croatian_match else "",
            'similarity_score': best_score,
            'biblical_ref': italian_biblical_ref
        })

        # Mark Croatian song as used if we found a match
        if best_croatian_match:
            used_croatian_songs.add(best_croatian_match)

    # PHASE 2: Force-match remaining Croatian songs to remaining Italian songs
    unmatched_croatian = [song for song in parsed_songs if song not in used_croatian_songs]
    unmatched_italian_indices = [i for i, match in enumerate(matches) if not match['matched_parsed_song']]

    print(f"Phase 2: Force-matching {len(unmatched_croatian)} remaining Croatian songs to {len(unmatched_italian_indices)} Italian songs...")

    # For each unmatched Croatian song, find the best available Italian song
    for croatian_song in unmatched_croatian:
        best_italian_index = None
        best_score = -1.0  # Allow any score, even 0

        croatian_title, croatian_ref = extract_croatian_parts(croatian_song)

        for i in unmatched_italian_indices:
            if matches[i]['matched_parsed_song']:  # Skip if already matched in this phase
                continue

            italian_data = translation_data[i]
            italian_title_clean, italian_ref = extract_italian_parts(italian_data['italian'])

            # Calculate similarity
            score = 0.0
            if italian_title_clean and croatian_title:
                score = max(
                    similarity(italian_title_clean, croatian_title),
                    similarity(normalize_for_comparison(italian_title_clean), normalize_for_comparison(croatian_title))
                )

            # Add Google translate similarity
            if italian_data['google_translate']:
                google_score = similarity(italian_data['google_translate'], croatian_song) * 0.5
                score = max(score, google_score)

            if score > best_score:
                best_score = score
                best_italian_index = i

        # Assign the best match
        if best_italian_index is not None:
            matches[best_italian_index]['matched_parsed_song'] = croatian_song
            matches[best_italian_index]['similarity_score'] = best_score
            unmatched_italian_indices.remove(best_italian_index)

    # Final check - should have no unmatched Croatian songs
    final_unmatched = [song for song in parsed_songs if song not in [m['matched_parsed_song'] for m in matches if m['matched_parsed_song']]]

    return matches, final_unmatched

def main():
    print("🎵 Croatian Song Matching Tool")
    print("=" * 50)
    
    # Parse translation file
    translation_file = "LISTA-IT-GOOGLE-HR.md"
    if not os.path.exists(translation_file):
        print(f"❌ Translation file not found: {translation_file}")
        return
    
    print(f"📖 Reading translation data from: {translation_file}")
    translation_data = parse_translation_file(translation_file)
    print(f"✅ Found {len(translation_data)} songs in translation list")
    
    # Get parsed Croatian songs
    chordpro_folder = "lang/hr/04_chordpro"
    print(f"📁 Reading parsed Croatian songs from: {chordpro_folder}")
    parsed_songs = get_parsed_croatian_songs(chordpro_folder)
    print(f"✅ Found {len(parsed_songs)} parsed Croatian songs")
    
    # Find matches
    print("\n🔍 Finding matches...")
    matches, unmatched = find_matches(translation_data, parsed_songs)
    
    # Sort matches by Italian ID for better display (preserving the actual matches)
    matches_sorted = sorted(matches, key=lambda x: int(x['italian_id']))

    # Display results
    print(f"\n✅ MATCHED SONGS ({len(matches_sorted)}):")
    print("-" * 80)
    for match in matches_sorted:
        score_indicator = "🎯" if match['similarity_score'] >= 0.9 else f"📊 {match['similarity_score']:.2f}"
        biblical_ref = f" ({match['biblical_ref']})" if match['biblical_ref'] else ""
        print(f"{match['italian_id']:>3} {score_indicator} {match['matched_parsed_song']}{biblical_ref}")
    
    print(f"\n❓ UNMATCHED PARSED SONGS ({len(unmatched)}):")
    print("-" * 80)
    for song in unmatched:
        print(f"    ❓ {song}")
    
    # Save results
    output_file = "croatian_song_matches.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Croatian Song Matches\n\n")
        f.write("## Matched Songs\n\n")
        f.write("| Italian ID | Italian Title | Croatian Title |\n")
        f.write("|----|----|----|\\n")

        for match in matches_sorted:
            f.write(f"| {match['italian_id']} | {match['italian']} | {match['matched_parsed_song']} |\n")
        
        f.write(f"\n## Unmatched Songs ({len(unmatched)})\n\n")
        for song in unmatched:
            f.write(f"- {song}\n")
    
    print(f"\n💾 Results saved to: {output_file}")

if __name__ == "__main__":
    main()
