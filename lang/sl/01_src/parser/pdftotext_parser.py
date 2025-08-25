#!/usr/bin/env python3
"""
Phase 3 PDFtoText Parser
Simplified parser using pdftotext for single-column PDFs with multi-page support.
Leverages the superior space-based precision of pdftotext for chord positioning.
Adapted from the proven git/new_parser approach.
"""

import subprocess
import tempfile
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
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
    original_line: str  # Keep original for precise positioning

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

class PDFtoTextParser:
    def __init__(self):
        self.role_markers = ['K.+Z.', 'K.', 'Z.', 'P.']
        self.pdftotext_available = self.check_pdftotext()

        # Croatian chord system (correct notation)
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

        print(f"🎸 Initialized with {len(self.valid_chords)} valid chords")

    def check_pdftotext(self) -> bool:
        """Check if pdftotext is available"""
        try:
            subprocess.run(['pdftotext', '-v'], capture_output=True, text=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text using pdftotext with layout preservation"""
        if not self.pdftotext_available:
            raise Exception("pdftotext not available")

        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                temp_path = temp_file.name

            # Use layout mode for precise positioning
            cmd = ['pdftotext', '-layout', '-enc', 'UTF-8', pdf_path, temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"pdftotext failed: {result.stderr}")

            with open(temp_path, 'r', encoding='utf-8') as f:
                text = f.read()

            os.unlink(temp_path)
            return text

        except Exception as e:
            raise Exception(f"Error extracting text: {e}")

    def parse_multi_page_pdf(self, pdf_files: List[str], song_name: str = "") -> Song:
        """Parse song from multiple PDF pages"""
        print(f"🎵 PDFtoText parsing: {song_name or 'Multi-page song'}")

        all_lines = []

        for i, pdf_file in enumerate(pdf_files):
            print(f"📄 Processing page {i+1}: {Path(pdf_file).name}")
            text = self.extract_text_from_pdf(pdf_file)

            # Split into lines and clean
            lines = text.split('\n')

            for line in lines:
                # Skip completely empty lines and page numbers
                if line.strip() and not line.strip().isdigit():
                    all_lines.append(line)

        print(f"📊 Total lines: {len(all_lines)}")

        # Parse into song structure
        song = self._parse_lines_to_song(all_lines, song_name)

        return song

    def _parse_lines_to_song(self, lines: List[str], song_name: str) -> Song:
        """Parse text lines into song structure with precise chord positioning"""
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
            line_clean = line.strip()
            if not line_clean:
                continue

            # Skip Kapodaster lines
            if 'kapodaster' in line_clean.lower() or 'kapo' in line_clean.lower():
                continue

            # Get position of first character (for center detection)
            first_char_pos = len(line) - len(line.lstrip())

            # Look for title - relaxed center detection for Croatian titles
            if (line_clean.isupper() and
                first_char_pos >= 0 and  # Any position (Croatian titles may not be perfectly centered)
                len(line_clean) > 10 and  # Reasonable length for title
                not any(char in line_clean for char in ['[', ']']) and  # No chords
                not self._is_chord_line(line_clean) and  # Not a chord line
                not any(role in line_clean for role in self.role_markers)):  # No role markers

                title = line_clean
                remaining_lines = lines[i+1:]  # Remove title from processing
                print(f"📋 TITLE: '{title}'")
                break

        return title, remaining_lines

    def _detect_kapodaster(self, lines: List[str]) -> Tuple[str, List[str]]:
        """Detect and extract Kapodaster line"""
        kapodaster = ""
        remaining_lines = lines[:]

        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            line_clean = line.strip()
            if not line_clean:
                continue

            # Look for Kapodaster lines
            if 'kapodaster' in line_clean.lower() or 'kapo' in line_clean.lower():
                kapodaster = line_clean
                remaining_lines = lines[i+1:]  # Remove kapodaster from processing
                print(f"🎸 KAPODASTER: '{kapodaster}'")
                break

        return kapodaster, remaining_lines

    def _find_chord_line_above(self, lines: List[str], current_index: int) -> List[ChordPosition]:
        """Find the nearest chord line above the current text line"""
        # Search backwards from current position
        for j in range(current_index - 1, -1, -1):
            line = lines[j]

            # Skip empty lines
            if not line.strip():
                continue

            # If we find a chord line, extract chords from it
            if self._is_chord_line(line):
                chords = self._extract_chords_from_line(line)
                print(f"      🔍 Found chord line above at index {j}: '{line.strip()}'")
                return chords

            # If we find a text line with role marker or other content, stop searching
            # (this prevents associating chords from a different verse)
            if (self._extract_role_marker(line) or
                (line.strip() and not self._is_chord_line(line) and not self._is_comment_line(line))):
                print(f"      🛑 Stopped chord search at text line: '{line.strip()}'")
                break

        return []

    def _parse_verses_with_chords(self, lines: List[str]) -> Tuple[List[Verse], List[str]]:
        """Parse lines into verses with precise chord positioning and extract comments"""
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
                # Collect multi-line comment
                comment_lines = [line.strip()]
                i += 1

                # Continue collecting until we find the closing parenthesis
                while i < len(lines) and not comment_lines[-1].rstrip().endswith(')'):
                    if lines[i].strip():
                        comment_lines.append(lines[i].strip())
                    i += 1

                # Join multi-line comment
                full_comment = '\n'.join(comment_lines)
                comments.append(full_comment)
                print(f"💬 COMMENT: '{full_comment}'")
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

                # Find chords above this line using improved search
                chords = self._find_chord_line_above(lines, i)

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
                    # Find chords above this line using improved search
                    chords = self._find_chord_line_above(lines, i)

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

    def _is_comment_line(self, line: str) -> bool:
        """Check if line is a comment (text in parentheses)"""
        line_clean = line.strip()
        return (line_clean.startswith('(') and
                ('slijedi' in line_clean.lower() or
                 'bez:' in line_clean.lower() or
                 ')' in line_clean))  # Contains closing parenthesis

    def _extract_role_marker(self, line: str) -> str:
        """Extract role marker from line"""
        for role in sorted(self.role_markers, key=len, reverse=True):
            if line.strip().startswith(role):
                return role
        return ""

    def _is_chord_line(self, line: str) -> bool:
        """Check if a line is primarily chords (adapted from existing converter)"""
        if not line.strip():
            return False

        line_clean = line.strip()
        words = line_clean.split()

        if not words:
            return False

        chord_count = 0
        for word in words:
            if self._looks_like_chord(word):
                chord_count += 1

        # If more than 60% are chords, consider it a chord line
        return (chord_count / len(words)) > 0.6

    def _looks_like_chord(self, word: str) -> bool:
        """Check if a word looks like a chord (adapted from existing converter)"""
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

    def _extract_chords_from_line(self, chord_line: str) -> List[ChordPosition]:
        """Extract chords and their positions from a chord line (adapted from existing converter)"""
        chords = []

        # Find all potential chords and their positions
        words = chord_line.split()
        current_pos = 0

        for word in words:
            # Find the position of this word in the original line
            word_pos = chord_line.find(word, current_pos)
            if word_pos >= 0:
                if self._looks_like_chord(word):
                    # Check if it's a compound chord like "FE" → "F E"
                    split_chords = self._split_compound_chord(word)

                    if len(split_chords) > 1:
                        # Multiple chords in one word
                        char_pos = word_pos
                        for split_chord in split_chords:
                            chords.append(ChordPosition(
                                chord=split_chord,
                                position=char_pos,
                                end_position=char_pos + len(split_chord)
                            ))
                            print(f"      🎸 Chord '{split_chord}' at position {char_pos}")
                            char_pos += len(split_chord)
                    else:
                        # Single valid chord
                        chords.append(ChordPosition(
                            chord=word,
                            position=word_pos,
                            end_position=word_pos + len(word)
                        ))
                        print(f"      🎸 Chord '{word}' at position {word_pos}")

                current_pos = word_pos + len(word)

        return chords

    def _split_compound_chord(self, word: str) -> List[str]:
        """Split compound chords like 'FE' into ['F', 'E']"""
        if word in self.valid_chords:
            return [word]  # Already a valid single chord

        # Try to split into valid chord combinations
        for i in range(1, len(word)):
            left_part = word[:i]
            right_part = word[i:]

            if (left_part in self.valid_chords and
                right_part in self.valid_chords):
                # Found valid split, check if there are more splits possible
                remaining_splits = self._split_compound_chord(right_part)
                return [left_part] + remaining_splits

        return [word]  # Can't split, return as-is

def main():
    parser = argparse.ArgumentParser(description='Parse single-column PDFs with pdftotext')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output name for display')

    args = parser.parse_args()

    pdf_parser = PDFtoTextParser()

    if not pdf_parser.pdftotext_available:
        print("❌ pdftotext not available")
        return

    # Parse the song
    song = pdf_parser.parse_multi_page_pdf(args.input, args.output or "Parsed Song")

    print(f"\n✅ PDFtoText Parser Results:")
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