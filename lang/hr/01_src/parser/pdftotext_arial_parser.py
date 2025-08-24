#!/usr/bin/env python3
"""
Enhanced pdftotext parser with Arial font-aware chord positioning
Uses actual Arial font character widths for precise chord positioning
"""

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
    end_position: int

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

class PDFToTextArialParser:
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

        print(f"🎸 Initialized Arial-aware pdftotext parser with {len(self.valid_chords)} valid chords")

    def get_char_width(self, char: str, font_size: float) -> float:
        """Get the actual width of a character in Arial font at given size"""
        font_units = self.arial_char_widths.get(char, 556)  # 556 is average Arial character width
        return (font_units / 1000.0) * font_size

    def find_char_position_from_spaces(self, text: str, font_size: float, space_position: int) -> int:
        """Convert space-based position from pdftotext to actual character position using Arial metrics"""
        
        # Calculate the width that the space_position represents
        # Assume each "space" in pdftotext represents approximately one average character width
        avg_char_width = self.get_char_width('n', font_size)  # Use 'n' as average character
        target_width = space_position * avg_char_width
        
        # Find the character position that corresponds to this width
        current_width = 0.0
        for i, char in enumerate(text):
            char_width = self.get_char_width(char, font_size)
            
            # If we're within this character's width, return this position
            if current_width + char_width/2 >= target_width:
                return i
            
            current_width += char_width
        
        # If we're past the end of the text, return the end position
        return len(text)

    def parse_multi_page_pdf(self, pdf_files: List[str], song_name: str = "") -> Song:
        """Parse song from multiple PDF pages using enhanced pdftotext"""
        print(f"🎵 Arial-aware pdftotext parsing: {song_name or 'Multi-page song'}")

        # Extract text using pdftotext
        all_lines = []
        for i, pdf_file in enumerate(pdf_files):
            print(f"📄 Processing page {i+1}: {Path(pdf_file).name}")
            lines = self._extract_pdftotext_lines(pdf_file)
            all_lines.extend(lines)

        print(f"📊 Total lines: {len(all_lines)}")

        # Parse into song structure
        song = self._parse_lines_to_song(all_lines, song_name)

        return song

    def _extract_pdftotext_lines(self, pdf_path: str) -> List[str]:
        """Extract text lines using pdftotext"""
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

    def _parse_lines_to_song(self, lines: List[str], song_name: str) -> Song:
        """Parse text lines into song structure with Arial-aware chord positioning"""
        # Detect title
        title, content_lines = self._detect_title(lines)
        if not title:
            title = song_name or "Untitled Song"

        # Detect Kapodaster
        kapodaster, content_lines = self._detect_kapodaster(content_lines)

        # Parse verses with chord-lyric pairing and extract comments
        verses, comments = self._parse_verses_with_chords(content_lines)

        return Song(title=title, kapodaster=kapodaster, verses=verses, comments=comments)

    def _detect_title(self, lines: List[str]) -> Tuple[str, List[str]]:
        """Detect and extract title from first few lines"""
        title = ""
        remaining_lines = lines[:]

        for i, line in enumerate(lines[:10]):
            if not line.strip():
                continue

            # Skip Kapodaster lines
            if 'kapodaster' in line.lower() or 'kapo' in line.lower():
                continue

            # Look for title - check if it's uppercase and centered-ish
            if (line.strip().isupper() and
                len(line.strip()) > 10 and  # Reasonable length for title
                not any(char in line for char in ['[', ']']) and  # No chords
                not self._is_chord_line(line) and  # Not a chord line
                not any(role in line for role in self.role_markers)):  # No role markers

                title = line.strip()
                remaining_lines = lines[i+1:]  # Remove title from processing
                print(f"📋 TITLE: '{title}'")
                break

        return title, remaining_lines

    def _detect_kapodaster(self, lines: List[str]) -> Tuple[str, List[str]]:
        """Detect and extract Kapodaster line"""
        kapodaster = ""
        remaining_lines = lines[:]

        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            if not line.strip():
                continue

            # Look for Kapodaster lines
            if 'kapodaster' in line.lower() or 'kapo' in line.lower():
                kapodaster = line.strip()
                remaining_lines = lines[i+1:]  # Remove kapodaster from processing
                print(f"🎸 KAPODASTER: '{kapodaster}'")
                break

        return kapodaster, remaining_lines

    def _is_chord_line(self, line: str) -> bool:
        """Check if a line is primarily chords"""
        words = line.split()
        if not words:
            return False

        chord_count = 0
        for word in words:
            if self._looks_like_chord(word):
                chord_count += 1

        # If more than 60% are chords, consider it a chord line
        return (chord_count / len(words)) > 0.6

    def _looks_like_chord(self, word: str) -> bool:
        """Check if a word looks like a chord"""
        if word in self.valid_chords:
            return True

        # Check for compound chords like "H7 a" or "FE" (F+E)
        if ' ' in word:
            parts = word.split()
            return any(part in self.valid_chords for part in parts)

        # Check for compound chords without spaces like "FE" → "F" + "E"
        if len(word) > 1:
            # Try to split into valid chord combinations
            for i in range(1, len(word)):
                left_part = word[:i]
                right_part = word[i:]
                if (left_part in self.valid_chords and
                    right_part in self.valid_chords):
                    return True

        return False

    def _parse_verses_with_chords(self, lines: List[str]) -> Tuple[List[Verse], List[str]]:
        """Parse lines into verses with Arial-aware chord positioning"""
        verses = []
        comments = []
        current_verse_lines = []
        current_role = ""

        i = 0
        while i < len(lines):
            line = lines[i]

            if not line.strip():
                i += 1
                continue

            # Check for comment (text in parentheses)
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

                # Find chords above this line using Arial-aware positioning
                chords = self._find_chord_line_above_arial(lines, i)

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
                    # Find chords above this line using Arial-aware positioning
                    chords = self._find_chord_line_above_arial(lines, i)

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

    def _find_chord_line_above_arial(self, lines: List[str], current_index: int) -> List[ChordPosition]:
        """Find the nearest chord line above the current text line with Arial-aware positioning"""
        # Search backwards from current position
        for j in range(current_index - 1, -1, -1):
            line = lines[j]

            # Skip empty lines
            if not line.strip():
                continue

            # If we find a chord line, extract chords from it using Arial metrics
            if self._is_chord_line(line):
                chords = self._extract_chords_from_line_arial(line, lines[current_index])
                print(f"      🔍 Found chord line above at index {j}: '{line.strip()}'")
                return chords

            # If we find a text line with role marker or other content, stop searching
            if (self._extract_role_marker(line) or
                (line.strip() and not self._is_chord_line(line) and not self._is_comment_line(line))):
                print(f"      🛑 Stopped chord search at text line: '{line.strip()}'")
                break

        return []

    def _extract_chords_from_line_arial(self, chord_line: str, text_line: str) -> List[ChordPosition]:
        """Extract chords from chord line and position them using Arial font metrics"""
        chords = []

        if not chord_line.strip() or not text_line.strip():
            return chords

        # Extract the text part (after role marker if present)
        text_content = text_line
        role_marker = self._extract_role_marker(text_line)
        if role_marker:
            text_content = text_line[len(role_marker):].strip()

        print(f"      📝 Text content: '{text_content}'")
        print(f"      🎼 Chord line: '{chord_line}'")

        # Font size for Arial text (from PyMuPDF analysis)
        font_size = 11.0

        # Parse individual chords from the chord line
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
                # Convert space-based position to Arial character position
                char_position = self.find_char_position_from_spaces(text_content, font_size, chord_start)

                # Ensure position is within text bounds
                char_position = max(0, min(char_position, len(text_content)))

                chords.append(ChordPosition(
                    chord=chord_word,
                    position=char_position,
                    end_position=char_position + len(chord_word)
                ))
                print(f"      🎸 Chord '{chord_word}' at space_pos={chord_start}, arial_char_pos={char_position}")

        return sorted(chords, key=lambda x: x.position)

    def _is_comment_line(self, line: str) -> bool:
        """Check if line is a comment (text in parentheses)"""
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

def main():
    parser = argparse.ArgumentParser(description='Parse single-column PDFs with Arial-aware pdftotext')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output name for display')

    args = parser.parse_args()

    pdf_parser = PDFToTextArialParser()

    # Parse the song
    song = pdf_parser.parse_multi_page_pdf(args.input, args.output or "Parsed Song")

    print(f"\n✅ Arial-aware Parser Results:")
    print(f"   🎵 Title: {song.title}")
    print(f"   🎭 Verses: {len(song.verses)}")

    # Display parsed structure with chord info
    for i, verse in enumerate(song.verses):
        print(f"   {i+1}. {verse.role} ({len(verse.lines)} lines)")
        for j, line in enumerate(verse.lines):
            chord_info = f" [{', '.join([f'{c.chord}@{c.position}' for c in line.chords])}]" if line.chords else ""
            print(f"      {j+1}. {line.text[:50]}...{chord_info}")

if __name__ == "__main__":
    main()
