#!/usr/bin/env python3
"""
Hybrid Corrected Parser - The REAL Magical Solution
Uses pdftotext spacing + PyMuPDF pixel coordinates + Arial font metrics
for the most accurate chord positioning possible
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

class HybridCorrectedParser:
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

        print(f"🎸 Initialized Hybrid Corrected Parser with {len(self.valid_chords)} valid chords")

    def get_char_width(self, char: str, font_size: float) -> float:
        """Get the actual width of a character in Arial font at given size"""
        font_units = self.arial_char_widths.get(char, 556)  # 556 is average Arial character width
        return (font_units / 1000.0) * font_size

    def calculate_scaling_factor(self, pdftotext_line: str, pymupdf_text_width: float, font_size: float) -> float:
        """Calculate the scaling factor between pdftotext spacing and actual pixel width"""
        
        # Calculate actual text width using Arial metrics
        actual_text_width = 0.0
        for char in pdftotext_line:
            actual_text_width += self.get_char_width(char, font_size)
        
        # Calculate pdftotext "character width" (total line length / number of characters)
        pdftotext_char_width = len(pdftotext_line)
        
        if pdftotext_char_width == 0:
            return 1.0
        
        # Scaling factor: how much should we scale pdftotext positions to match actual pixels
        scaling_factor = actual_text_width / (pdftotext_char_width * self.get_char_width('n', font_size))
        
        return scaling_factor

    def correct_chord_positions(self, chord_line: str, text_line: str, text_start_x: float, font_size: float) -> List[ChordPosition]:
        """Correct chord positions using hybrid approach"""
        chords = []
        
        # Extract text content (after role marker)
        role_marker = self._extract_role_marker(text_line)
        text_content = text_line[len(role_marker):].strip() if role_marker else text_line.strip()
        
        print(f"      📝 Text: '{text_content}'")
        print(f"      🎼 Chord line: '{chord_line}'")
        print(f"      📏 Text starts at X={text_start_x:.1f}, font_size={font_size}")
        
        # Calculate scaling factor
        scaling_factor = self.calculate_scaling_factor(text_content, 0, font_size)  # We'll refine this
        
        print(f"      ⚖️ Scaling factor: {scaling_factor:.3f}")
        
        # Parse chords from pdftotext chord line
        i = 0
        while i < len(chord_line):
            char = chord_line[i]
            
            # Skip spaces
            if char.isspace():
                i += 1
                continue
            
            # Found start of a potential chord
            chord_start = i
            chord_word = ""
            
            # Extract the chord word (non-space characters)
            while i < len(chord_line) and not chord_line[i].isspace():
                chord_word += chord_line[i]
                i += 1
            
            # Check if it's a valid chord
            if self._looks_like_chord(chord_word):
                # Convert pdftotext position to corrected character position
                # This is the key correction using Arial font metrics
                
                # Method 1: Simple proportional scaling
                char_position = int((chord_start / len(chord_line)) * len(text_content))
                
                # Method 2: More sophisticated approach using actual character widths
                # Calculate what pixel position this chord_start represents
                avg_char_width = self.get_char_width('n', font_size)
                estimated_pixel_offset = chord_start * avg_char_width * scaling_factor
                
                # Find the character position that corresponds to this pixel offset
                current_pixel_offset = 0.0
                corrected_char_position = 0
                
                for j, char in enumerate(text_content):
                    char_width = self.get_char_width(char, font_size)
                    if current_pixel_offset + char_width/2 >= estimated_pixel_offset:
                        corrected_char_position = j
                        break
                    current_pixel_offset += char_width
                
                # Use the more sophisticated method
                final_char_position = min(corrected_char_position, len(text_content))
                
                chords.append(ChordPosition(
                    chord=chord_word,
                    position=final_char_position,
                    x_coord=text_start_x + estimated_pixel_offset
                ))
                
                char_at_pos = text_content[final_char_position] if final_char_position < len(text_content) else 'END'
                print(f"      🎸 Chord '{chord_word}' at pdftotext_pos={chord_start} -> corrected_pos={final_char_position} ('{char_at_pos}')")

        return sorted(chords, key=lambda x: x.position)

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files using hybrid corrected approach and export to ChordPro format"""
        print(f"🎵 Hybrid Corrected parsing: {song_name or 'Multi-page song'}")

        # Step 1: Extract pdftotext data for spacing information
        pdftotext_lines = self._extract_pdftotext_data(pdf_files[0])
        
        # Step 2: Extract PyMuPDF data for pixel coordinates
        pymupdf_data = self._extract_pymupdf_data(pdf_files[0])
        
        # Step 3: Combine using hybrid correction
        song = self._parse_with_hybrid_correction(pdftotext_lines, pymupdf_data, song_name)
        
        # Step 4: Export to ChordPro format
        return self._export_to_chordpro(song)

    def _extract_pdftotext_data(self, pdf_path: str) -> List[str]:
        """Extract text lines from pdftotext"""
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

    def _extract_pymupdf_data(self, pdf_path: str) -> Dict:
        """Extract pixel coordinate data from PyMuPDF"""
        doc = fitz.open(pdf_path)
        page = doc[0]
        text_dict = page.get_text("dict")

        text_lines_by_content = {}  # Map text content to pixel coordinates

        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    line_start_x = None
                    font_size = 11.0
                    
                    for span in line["spans"]:
                        if span['text'].strip():
                            line_text += span['text']
                            if line_start_x is None:
                                line_start_x = span['bbox'][0]
                            font_size = span.get('size', 11.0)
                    
                    if line_text.strip():
                        # Clean up the text for matching
                        clean_text = line_text.strip()
                        text_lines_by_content[clean_text] = {
                            'start_x': line_start_x,
                            'font_size': font_size,
                            'y': line["bbox"][1]
                        }

        doc.close()
        return text_lines_by_content

    def _parse_with_hybrid_correction(self, pdftotext_lines: List[str], pymupdf_data: Dict, song_name: str) -> Song:
        """Parse using hybrid correction approach"""
        
        # Parse pdftotext lines for structure
        title, content_lines = self._detect_title_from_pdftotext(pdftotext_lines)
        if not title:
            title = song_name or "Untitled Song"

        kapodaster, content_lines = self._detect_kapodaster_from_pdftotext(content_lines)
        
        # Parse verses with hybrid correction
        verses, comments = self._parse_verses_with_hybrid_correction(content_lines, pymupdf_data)

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

    def _parse_verses_with_hybrid_correction(self, pdftotext_lines: List[str], pymupdf_data: Dict) -> Tuple[List[Verse], List[str]]:
        """Parse verses using hybrid correction approach"""
        verses = []
        comments = []
        current_verse_lines = []
        current_role = ""

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

                # Find chords using hybrid correction
                chords = self._find_chords_with_hybrid_correction(pdftotext_lines, i, pymupdf_data)

                verse_line = VerseLine(
                    text=text_after_role,
                    chords=chords,
                    original_line=line
                )
                current_verse_lines = [verse_line]
                print(f"🎵 Started verse: {current_role}")

            elif current_role:
                # Continuation line in current verse
                if not self._is_chord_line(line):
                    # Find chords using hybrid correction
                    chords = self._find_chords_with_hybrid_correction(pdftotext_lines, i, pymupdf_data)

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

    def _find_chords_with_hybrid_correction(self, pdftotext_lines: List[str], current_index: int, pymupdf_data: Dict) -> List[ChordPosition]:
        """Find chords using hybrid correction approach"""

        # Find chord line above current text line
        chord_line = None
        text_line = pdftotext_lines[current_index]

        for j in range(current_index - 1, -1, -1):
            line = pdftotext_lines[j]

            # Skip empty lines
            if not line.strip():
                continue

            # If we find a chord line, use it
            if self._is_chord_line(line):
                chord_line = line
                print(f"      🔍 Found chord line above: '{line.strip()}'")
                break

            # If we find another text line, stop searching
            if (self._extract_role_marker(line) or
                (line.strip() and not self._is_chord_line(line) and not self._is_comment_line(line))):
                print(f"      🛑 Stopped chord search at text line: '{line.strip()}'")
                break

        if not chord_line:
            return []

        # Find pixel coordinates for the text line
        role_marker = self._extract_role_marker(text_line)
        search_text = text_line[len(role_marker):].strip() if role_marker else text_line.strip()

        # Look for matching text in PyMuPDF data
        text_start_x = None
        font_size = 11.0

        for content, data in pymupdf_data.items():
            if search_text in content or content in search_text:
                text_start_x = data['start_x']
                font_size = data['font_size']
                print(f"      ✅ Found text coordinates: X={text_start_x:.1f}, font_size={font_size}")
                break

        if text_start_x is None:
            print(f"      ❌ Could not find text coordinates in PyMuPDF data")
            return []

        # Apply hybrid correction
        return self.correct_chord_positions(chord_line, text_line, text_start_x, font_size)

    def _is_chord_line(self, line: str) -> bool:
        """Check if a line is primarily chords"""
        words = line.split()
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
        """Position chords within lyric text using corrected positions"""
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
    parser = argparse.ArgumentParser(description='Hybrid Corrected Parser for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    hybrid_parser = HybridCorrectedParser()

    # Parse and export
    chordpro_content = hybrid_parser.parse_and_export(args.input, args.song_name or "")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {args.output}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
