#!/usr/bin/env python3
"""
Pixel-Precise Parser for Croatian Songs
Uses PyMuPDF pixel coordinates + Arial font metrics for exact character positioning
This is the "magical" approach to solve the proportional font spacing issue
"""

import fitz  # PyMuPDF
import subprocess
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import argparse

@dataclass
class ChordPosition:
    chord: str
    position: int
    x_coord: float  # Actual pixel position

@dataclass
class VerseLine:
    text: str
    chords: List[ChordPosition]
    original_line: str

@dataclass
class Verse:
    role: str
    lines: List[VerseLine]

@dataclass
class Song:
    title: str
    kapodaster: str
    verses: List[Verse]
    comments: List[str]

class PixelPreciseParser:
    def __init__(self):
        self.role_markers = ['K.+Z.', 'K.', 'Z.', 'P.']
        
        # Croatian chord system
        self.base_chords = {
            'minors': ['e', 'f', 'fis', 'g', 'gis', 'a', 'b', 'h', 'c', 'cis', 'd', 'dis'],
            'majors': ['E', 'F', 'FIS', 'G', 'GIS', 'A', 'B', 'H', 'C', 'CIS', 'D', 'DIS']
        }

        # Build complete chord list with variations
        self.valid_chords = set()
        for chord_list in self.base_chords.values():
            self.valid_chords.update(chord_list)
            for chord in chord_list:
                for num in ['7', '9', '11', '13']:
                    self.valid_chords.add(f"{chord}{num}")
                for suffix in ['sus2', 'sus4', 'maj7', 'min7', 'dim', 'aug', 'add9']:
                    self.valid_chords.add(f"{chord}{suffix}")

        # Add special symbols
        self.valid_chords.update(['*', 'd*'])

        # Arial font character widths (in font units, 1000 units per em)
        self.arial_char_widths = {
            'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278, 'J': 500,
            'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611,
            'U': 722, 'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611,
            'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556, 'h': 556, 'i': 222, 'j': 222,
            'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556, 'p': 556, 'q': 556, 'r': 333, 's': 500, 't': 278,
            'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500,
            ' ': 278, '.': 278, ',': 278, ':': 278, ';': 278, '!': 333, '?': 556, '"': 355, "'": 191,
            '(': 333, ')': 333, '[': 278, ']': 278, '{': 334, '}': 334, '-': 333, '_': 556, '=': 584,
            '+': 584, '*': 389, '/': 278, '\\': 278, '|': 260, '&': 667, '%': 889, '$': 556, '#': 556,
            '@': 1015, '^': 469, '~': 584, '`': 333, '0': 556, '1': 556, '2': 556, '3': 556, '4': 556,
            '5': 556, '6': 556, '7': 556, '8': 556, '9': 556
        }

        print(f"🎸 Initialized Pixel-Precise Parser with {len(self.valid_chords)} valid chords")

    def get_char_width(self, char: str, font_size: float) -> float:
        """Get the actual width of a character in Arial font at given size"""
        font_units = self.arial_char_widths.get(char, 556)  # 556 is average Arial character width
        return (font_units / 1000.0) * font_size

    def build_character_position_map(self, text: str, font_size: float, text_start_x: float) -> List[Tuple[int, float, float]]:
        """Build a map of character positions with their pixel coordinates"""
        char_map = []
        current_x = text_start_x
        
        for i, char in enumerate(text):
            char_width = self.get_char_width(char, font_size)
            char_start_x = current_x
            char_end_x = current_x + char_width
            
            char_map.append((i, char_start_x, char_end_x))
            current_x = char_end_x
        
        return char_map

    def find_char_position_from_pixel(self, char_map: List[Tuple[int, float, float]], chord_x: float) -> int:
        """Find the character position that best matches the chord's pixel position"""
        best_pos = 0
        min_distance = float('inf')
        
        for char_pos, char_start_x, char_end_x in char_map:
            # Calculate distance from chord position to character center
            char_center_x = (char_start_x + char_end_x) / 2
            distance = abs(chord_x - char_center_x)
            
            if distance < min_distance:
                min_distance = distance
                best_pos = char_pos
        
        return best_pos

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files using pixel-precise approach and export to ChordPro format"""
        print(f"🎵 Pixel-Precise parsing: {song_name or 'Multi-page song'}")

        # Step 1: Extract precise positioning data from PyMuPDF
        pymupdf_data = self._extract_pymupdf_data(pdf_files[0])  # Assuming single page for now
        
        # Step 2: Extract clean text from pdftotext for structure
        pdftotext_lines = self._extract_pdftotext_data(pdf_files[0])
        
        # Step 3: Combine data using pixel-precise positioning
        song = self._combine_with_pixel_precision(pymupdf_data, pdftotext_lines, song_name)
        
        # Step 4: Export to ChordPro format
        return self._export_to_chordpro(song)

    def _extract_pymupdf_data(self, pdf_path: str) -> Dict:
        """Extract positioning data from PyMuPDF with pixel precision"""
        doc = fitz.open(pdf_path)
        page = doc[0]
        text_dict = page.get_text("dict")

        elements_by_y = {}  # Group elements by Y coordinate

        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_y = round(line["bbox"][1])  # Round Y coordinate for grouping
                    
                    if line_y not in elements_by_y:
                        elements_by_y[line_y] = []
                    
                    for span in line["spans"]:
                        if span['text'].strip():
                            elements_by_y[line_y].append({
                                'text': span['text'],
                                'x': span['bbox'][0],
                                'y': span['bbox'][1],
                                'font': span.get('font', ''),
                                'size': span.get('size', 12)
                            })

        doc.close()
        
        # Sort elements within each line by X coordinate
        for y in elements_by_y:
            elements_by_y[y].sort(key=lambda x: x['x'])
        
        return elements_by_y

    def _extract_pdftotext_data(self, pdf_path: str) -> List[str]:
        """Extract clean text lines from pdftotext for structure"""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            cmd = ['pdftotext', '-layout', '-enc', 'UTF-8', pdf_path, temp_path]
            subprocess.run(cmd, check=True)

            with open(temp_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            return [line.rstrip() for line in lines]
        
        finally:
            os.unlink(temp_path)

    def _combine_with_pixel_precision(self, pymupdf_data: Dict, pdftotext_lines: List[str], song_name: str) -> Song:
        """Combine PyMuPDF pixel data with pdftotext structure for precise positioning"""
        
        # Parse pdftotext lines for structure
        title, content_lines = self._detect_title_from_pdftotext(pdftotext_lines)
        if not title:
            title = song_name or "Untitled Song"

        kapodaster, content_lines = self._detect_kapodaster_from_pdftotext(content_lines)
        
        # Parse verses with pixel-precise chord positioning
        verses, comments = self._parse_verses_with_pixel_precision(content_lines, pymupdf_data)

        return Song(title=title, kapodaster=kapodaster, verses=verses, comments=comments)

    def _detect_title_from_pdftotext(self, lines: List[str]) -> Tuple[str, List[str]]:
        """Detect title from pdftotext lines"""
        title = ""
        remaining_lines = lines[:]

        for i, line in enumerate(lines[:10]):
            if not line.strip():
                continue

            # Skip Kapodaster lines
            if 'kapodaster' in line.lower() or 'kapo' in line.lower():
                continue

            # Look for title - uppercase, reasonable length, no role markers
            if (line.strip().isupper() and
                len(line.strip()) > 10 and
                not any(role in line for role in self.role_markers)):

                title = line.strip()
                remaining_lines = lines[i+1:]
                print(f"📋 TITLE: '{title}'")
                break

        return title, remaining_lines

    def _detect_kapodaster_from_pdftotext(self, lines: List[str]) -> Tuple[str, List[str]]:
        """Detect Kapodaster from pdftotext lines"""
        kapodaster = ""
        remaining_lines = lines[:]

        for i, line in enumerate(lines[:5]):
            if not line.strip():
                continue

            if 'kapodaster' in line.lower() or 'kapo' in line.lower():
                kapodaster = line.strip()
                remaining_lines = lines[i+1:]
                print(f"🎸 KAPODASTER: '{kapodaster}'")
                break

        return kapodaster, remaining_lines

    def _parse_verses_with_pixel_precision(self, pdftotext_lines: List[str], pymupdf_data: Dict) -> Tuple[List[Verse], List[str]]:
        """Parse verses using pixel-precise chord positioning"""
        verses = []
        comments = []
        current_verse_lines = []
        current_role = ""

        # Convert PyMuPDF data to a more usable format
        sorted_y_positions = sorted(pymupdf_data.keys())

        print(f"🔍 Found {len(sorted_y_positions)} lines in PyMuPDF data")

        i = 0
        while i < len(pdftotext_lines):
            line = pdftotext_lines[i]

            if not line.strip():
                i += 1
                continue

            # Check for comment
            if self._is_comment_line(line):
                comments.append(line.strip())
                print(f"💬 COMMENT: '{line.strip()}'")
                i += 1
                continue

            # Check for role marker
            role_marker = self._extract_role_marker(line)

            if role_marker:
                # Save previous verse if exists
                if current_verse_lines and current_role:
                    verses.append(Verse(role=current_role, lines=current_verse_lines))
                    print(f"🎭 Completed verse: {current_role} with {len(current_verse_lines)} lines")

                # Start new verse
                current_role = role_marker
                text_after_role = line[len(role_marker):].strip()

                # Find precise chord positions using pixel data
                chords = self._find_pixel_precise_chords(line, pymupdf_data, sorted_y_positions)

                verse_line = VerseLine(
                    text=text_after_role,
                    chords=chords,
                    original_line=line
                )
                current_verse_lines = [verse_line]
                print(f"🎵 Started verse: {current_role}")

            elif current_role:
                # Continuation line in current verse
                if not self._is_chord_line_text(line):
                    # Find precise chord positions using pixel data
                    chords = self._find_pixel_precise_chords(line, pymupdf_data, sorted_y_positions)

                    verse_line = VerseLine(
                        text=line.strip(),
                        chords=chords,
                        original_line=line
                    )
                    current_verse_lines.append(verse_line)

            i += 1

        # Add final verse
        if current_verse_lines and current_role:
            verses.append(Verse(role=current_role, lines=current_verse_lines))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines")

        return verses, comments

    def _find_pixel_precise_chords(self, text_line: str, pymupdf_data: Dict, sorted_y_positions: List[int]) -> List[ChordPosition]:
        """Find chords using pixel-precise positioning"""
        chords = []

        # Find the text line in PyMuPDF data by matching content
        text_elements = None
        text_y = None

        role_marker = self._extract_role_marker(text_line)
        search_text = text_line[len(role_marker):].strip() if role_marker else text_line.strip()

        print(f"      🔍 Searching for text: '{search_text}'")

        # Find matching text line in PyMuPDF data
        for y_pos in sorted_y_positions:
            elements = pymupdf_data[y_pos]
            combined_text = ''.join([elem['text'] for elem in elements]).strip()

            # Check if this line contains our text (allowing for partial matches)
            if search_text in combined_text or combined_text in search_text:
                text_elements = elements
                text_y = y_pos
                print(f"      ✅ Found matching text line at Y={y_pos}: '{combined_text}'")
                break

        if not text_elements:
            print(f"      ❌ Could not find matching text line in PyMuPDF data")
            return chords

        # Find chord line above this text line
        chord_elements = None
        for y_pos in reversed(sorted_y_positions):
            if y_pos >= text_y:
                continue

            elements = pymupdf_data[y_pos]
            combined_text = ''.join([elem['text'] for elem in elements]).strip()

            # Check if this looks like a chord line
            if self._is_chord_line_text(combined_text):
                chord_elements = elements
                print(f"      🎼 Found chord line at Y={y_pos}: '{combined_text}'")
                break

        if not chord_elements:
            print(f"      ❌ No chord line found above text")
            return chords

        # Now do pixel-precise positioning
        return self._calculate_pixel_precise_positions(chord_elements, text_elements, search_text)

    def _calculate_pixel_precise_positions(self, chord_elements: List[Dict], text_elements: List[Dict], text_content: str) -> List[ChordPosition]:
        """Calculate precise chord positions using pixel coordinates and Arial font metrics"""
        chords = []

        # Get font size from text elements
        font_size = text_elements[0]['size'] if text_elements else 11.0

        # Get text start position
        text_start_x = min(elem['x'] for elem in text_elements)

        print(f"      📏 Text starts at X={text_start_x:.1f}, font_size={font_size}")

        # Build character position map for the text
        char_map = self.build_character_position_map(text_content, font_size, text_start_x)

        print(f"      📝 Built character map for '{text_content}' ({len(char_map)} chars)")

        # Process each chord element
        for chord_elem in chord_elements:
            chord_text = chord_elem['text'].strip()
            chord_x = chord_elem['x']

            if not chord_text:
                continue

            # Extract individual chords from the element
            chord_words = chord_text.split()
            for word in chord_words:
                if self._looks_like_chord(word):
                    # Find the best character position for this chord
                    char_pos = self.find_char_position_from_pixel(char_map, chord_x)

                    chords.append(ChordPosition(
                        chord=word,
                        position=char_pos,
                        x_coord=chord_x
                    ))

                    char_at_pos = text_content[char_pos] if char_pos < len(text_content) else 'END'
                    print(f"      🎸 Chord '{word}' at X={chord_x:.1f} -> char_pos={char_pos} ('{char_at_pos}')")

        return sorted(chords, key=lambda x: x.position)

    def _is_chord_line_text(self, text: str) -> bool:
        """Check if text line contains primarily chords"""
        words = text.split()
        if not words:
            return False

        chord_count = 0
        for word in words:
            if self._looks_like_chord(word):
                chord_count += 1

        return (chord_count / len(words)) > 0.6

    def _looks_like_chord(self, word: str) -> bool:
        """Check if a word looks like a chord"""
        if word in self.valid_chords:
            return True

        # Check for compound chords
        if ' ' in word:
            parts = word.split()
            return any(part in self.valid_chords for part in parts)

        if len(word) > 1:
            for i in range(1, len(word)):
                left_part = word[:i]
                right_part = word[i:]
                if (left_part in self.valid_chords and
                    right_part in self.valid_chords):
                    return True

        return False

    def _is_comment_line(self, line: str) -> bool:
        """Check if line is a comment"""
        line_clean = line.strip()
        return (line_clean.startswith('(') and
                ('slijedi' in line_clean.lower() or
                 'bez:' in line_clean.lower() or
                 ')' in line_clean))

    def _extract_role_marker(self, line: str) -> str:
        """Extract role marker from line"""
        for role in sorted(self.role_markers, key=len, reverse=True):
            if line.strip().startswith(role):
                return role
        return ""

    def _export_to_chordpro(self, song: Song) -> str:
        """Export song to ChordPro format"""
        chordpro_lines = []

        # Add title
        if song.title:
            chordpro_lines.append(f"{{title: {song.title}}}")
            chordpro_lines.append("")

        # Add kapodaster if present
        if song.kapodaster:
            chordpro_lines.append(f"{{comment: {song.kapodaster}}}")
            chordpro_lines.append("")

        # Add comments
        for comment in song.comments:
            chordpro_lines.append(f"{{comment: {comment}}}")

        if song.comments:
            chordpro_lines.append("")

        # Process verses
        for verse in song.verses:
            for i, line in enumerate(verse.lines):
                if line.chords:
                    chordpro_line = self._position_chords_in_lyrics(line.chords, line.text)
                else:
                    chordpro_line = line.text

                # Add role prefix ONLY on first line of verse
                if i == 0:
                    chordpro_lines.append(f"{verse.role}\t{chordpro_line}")
                else:
                    chordpro_lines.append(f"\t{chordpro_line}")

            chordpro_lines.append("")

        return '\n'.join(chordpro_lines)

    def _position_chords_in_lyrics(self, chords: List[ChordPosition], lyric_text: str) -> str:
        """Position chords within lyric text using pixel-precise positions"""
        if not chords or not lyric_text.strip():
            if chords:
                chord_names = [c.chord for c in chords]
                return '[' + ']['.join(chord_names) + ']'
            else:
                return lyric_text

        result = ""
        lyric_pos = 0

        sorted_chords = sorted(chords, key=lambda x: x.position)

        for chord in sorted_chords:
            chord_pos = chord.position
            target_lyric_pos = min(chord_pos, len(lyric_text))

            if target_lyric_pos > lyric_pos:
                result += lyric_text[lyric_pos:target_lyric_pos]
                lyric_pos = target_lyric_pos

            result += f"[{chord.chord}]"

        if lyric_pos < len(lyric_text):
            result += lyric_text[lyric_pos:]

        return result

def main():
    parser = argparse.ArgumentParser(description='Pixel-Precise Parser for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    pixel_parser = PixelPreciseParser()

    # Parse and export
    chordpro_content = pixel_parser.parse_and_export(args.input, args.song_name or "")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {args.output}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
