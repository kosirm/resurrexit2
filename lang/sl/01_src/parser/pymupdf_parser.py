#!/usr/bin/env python3
"""
Phase 3 PyMuPDF Parser
Uses PyMuPDF for pixel-precise positioning and font-based character width calculation
to solve proportional font spacing issues in chord positioning.
Based on the proven ABBY solution approach.
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import argparse

@dataclass
class ChordPosition:
    chord: str
    position: int
    end_position: int
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

class PyMuPDFParser:
    def __init__(self):
        self.role_markers = ['K.+Z.', 'K.', 'Z.', 'P.']
        
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

        print(f"🎸 Initialized PyMuPDF parser with {len(self.valid_chords)} valid chords")

    def extract_text_elements(self, pdf_path: str) -> List[Dict]:
        """Extract text elements with precise positioning using PyMuPDF"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]  # First page

            # Get text as dictionary with detailed formatting
            text_dict = page.get_text("dict")

            text_elements = []

            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            # Extract font information
                            font_name = span.get('font', '')
                            font_size = span.get('size', 12)
                            font_flags = span.get('flags', 0)

                            text_elements.append({
                                'text': span['text'],
                                'bbox': span['bbox'],  # (x0, y0, x1, y1)
                                'font': font_name,
                                'size': font_size,
                                'flags': font_flags,
                                'x': span['bbox'][0],  # Left position
                                'y': span['bbox'][1],  # Top position
                                'width': span['bbox'][2] - span['bbox'][0],
                                'height': span['bbox'][3] - span['bbox'][1]
                            })

            doc.close()
            return text_elements

        except Exception as e:
            raise Exception(f"Error extracting text elements: {e}")

    def group_elements_by_lines(self, elements: List[Dict]) -> List[List[Dict]]:
        """Group text elements into lines based on Y coordinates"""
        if not elements:
            return []

        # Sort by Y coordinate first, then by X coordinate
        sorted_elements = sorted(elements, key=lambda x: (x['y'], x['x']))

        lines = []
        current_line = []
        current_y = None
        y_tolerance = 5  # Pixels tolerance for same line

        for element in sorted_elements:
            if current_y is None or abs(element['y'] - current_y) <= y_tolerance:
                current_line.append(element)
                current_y = element['y'] if current_y is None else current_y
            else:
                if current_line:
                    lines.append(current_line)
                current_line = [element]
                current_y = element['y']

        if current_line:
            lines.append(current_line)

        return lines

    def parse_multi_page_pdf(self, pdf_files: List[str], song_name: str = "") -> Song:
        """Parse song from multiple PDF pages using PyMuPDF"""
        print(f"🎵 PyMuPDF parsing: {song_name or 'Multi-page song'}")

        all_elements = []

        for i, pdf_file in enumerate(pdf_files):
            print(f"📄 Processing page {i+1}: {Path(pdf_file).name}")
            elements = self.extract_text_elements(pdf_file)
            all_elements.extend(elements)

        print(f"📊 Total text elements: {len(all_elements)}")

        # Group elements into lines
        lines = self.group_elements_by_lines(all_elements)
        print(f"📊 Total lines: {len(lines)}")

        # Parse into song structure
        song = self._parse_lines_to_song(lines, song_name)

        return song

    def _parse_lines_to_song(self, lines: List[List[Dict]], song_name: str) -> Song:
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

    def _detect_title(self, lines: List[List[Dict]]) -> Tuple[str, List[List[Dict]]]:
        """Detect and extract title from first few lines"""
        title = ""
        remaining_lines = lines[:]

        for i, line_elements in enumerate(lines[:10]):
            if not line_elements:
                continue

            # Combine text from all elements in the line
            line_text = ''.join([elem['text'] for elem in line_elements]).strip()
            
            if not line_text:
                continue

            # Skip Kapodaster lines
            if 'kapodaster' in line_text.lower() or 'kapo' in line_text.lower():
                continue

            # Look for title - check if it's uppercase and centered-ish
            if (line_text.isupper() and
                len(line_text) > 10 and  # Reasonable length for title
                not any(char in line_text for char in ['[', ']']) and  # No chords
                not self._is_chord_line_elements(line_elements) and  # Not a chord line
                not any(role in line_text for role in self.role_markers)):  # No role markers

                title = line_text
                remaining_lines = lines[i+1:]  # Remove title from processing
                print(f"📋 TITLE: '{title}'")
                break

        return title, remaining_lines

    def _detect_kapodaster(self, lines: List[List[Dict]]) -> Tuple[str, List[List[Dict]]]:
        """Detect and extract Kapodaster line"""
        kapodaster = ""
        remaining_lines = lines[:]

        for i, line_elements in enumerate(lines[:5]):  # Check first 5 lines
            if not line_elements:
                continue

            line_text = ''.join([elem['text'] for elem in line_elements]).strip()
            
            if not line_text:
                continue

            # Look for Kapodaster lines
            if 'kapodaster' in line_text.lower() or 'kapo' in line_text.lower():
                kapodaster = line_text
                remaining_lines = lines[i+1:]  # Remove kapodaster from processing
                print(f"🎸 KAPODASTER: '{kapodaster}'")
                break

        return kapodaster, remaining_lines

    def _is_chord_line_elements(self, line_elements: List[Dict]) -> bool:
        """Check if a line of elements is primarily chords"""
        if not line_elements:
            return False

        words = []
        for elem in line_elements:
            words.extend(elem['text'].split())

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

    def _parse_verses_with_chords(self, lines: List[List[Dict]]) -> Tuple[List[Verse], List[str]]:
        """Parse lines into verses with precise chord positioning using font-based calculations"""
        verses = []
        comments = []
        current_verse_lines = []
        current_role = ""

        i = 0
        while i < len(lines):
            line_elements = lines[i]

            if not line_elements:
                i += 1
                continue

            line_text = ''.join([elem['text'] for elem in line_elements]).strip()

            if not line_text:
                i += 1
                continue

            # Check for comment (text in parentheses)
            if self._is_comment_line(line_text):
                # Collect multi-line comment
                comment_lines = [line_text]
                i += 1

                # Continue collecting until we find the closing parenthesis
                while i < len(lines) and not comment_lines[-1].rstrip().endswith(')'):
                    if lines[i]:
                        next_line_text = ''.join([elem['text'] for elem in lines[i]]).strip()
                        if next_line_text:
                            comment_lines.append(next_line_text)
                    i += 1

                # Join multi-line comment
                full_comment = '\n'.join(comment_lines)
                comments.append(full_comment)
                print(f"💬 COMMENT: '{full_comment}'")
                continue

            # Check for role marker
            role_marker = self._extract_role_marker(line_text)

            if role_marker:
                # Save previous verse if exists
                if current_verse_lines and current_role:
                    verses.append(Verse(role=current_role, lines=current_verse_lines))
                    print(f"🎭 Completed verse: {current_role} with {len(current_verse_lines)} lines")

                # Start new verse
                current_role = role_marker
                text_after_role = line_text[len(role_marker):].strip()

                # Find chords above this line using improved search
                chords = self._find_chord_line_above(lines, i)

                verse_line = VerseLine(
                    text=text_after_role,
                    chords=chords,
                    original_line=line_text
                )
                current_verse_lines = [verse_line]
                print(f"🎵 Started verse: {current_role}")

            elif current_role:
                # Continuation line in current verse
                if not self._is_chord_line_elements(line_elements):
                    # Find chords above this line using improved search
                    chords = self._find_chord_line_above(lines, i)

                    verse_line = VerseLine(
                        text=line_text,
                        chords=chords,
                        original_line=line_text
                    )
                    current_verse_lines.append(verse_line)

            i += 1

        # Add final verse
        if current_verse_lines and current_role:
            verses.append(Verse(role=current_role, lines=current_verse_lines))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines")

        return verses, comments

    def _find_chord_line_above(self, lines: List[List[Dict]], current_index: int) -> List[ChordPosition]:
        """Find the nearest chord line above the current text line with font-based positioning"""
        # Search backwards from current position
        for j in range(current_index - 1, -1, -1):
            line_elements = lines[j]

            if not line_elements:
                continue

            line_text = ''.join([elem['text'] for elem in line_elements]).strip()

            # If we find a chord line, extract chords from it
            if self._is_chord_line_elements(line_elements):
                chords = self._extract_chords_from_elements(line_elements, lines[current_index])
                print(f"      🔍 Found chord line above at index {j}: '{line_text}'")
                return chords

            # If we find a text line with role marker or other content, stop searching
            if (self._extract_role_marker(line_text) or
                (line_text and not self._is_chord_line_elements(line_elements) and not self._is_comment_line(line_text))):
                print(f"      🛑 Stopped chord search at text line: '{line_text}'")
                break

        return []

    def _extract_chords_from_elements(self, chord_elements: List[Dict], text_elements: List[Dict]) -> List[ChordPosition]:
        """Extract chords and calculate their positions using font-based character width"""
        chords = []

        if not text_elements:
            return chords

        # Calculate average font size from text elements for character width estimation
        text_font_sizes = [elem['size'] for elem in text_elements if elem['size'] > 0]
        avg_font_size = sum(text_font_sizes) / len(text_font_sizes) if text_font_sizes else 12

        # Font-based character width calculation (from ABBY documentation)
        estimated_char_width = avg_font_size * 0.5  # Times New Roman ratio

        # Get the starting X position of the text line
        text_start_x = min(elem['x'] for elem in text_elements)

        # Combine all text to get the full text line
        full_text = ''.join([elem['text'] for elem in text_elements])

        print(f"      📏 Font analysis: avg_size={avg_font_size:.1f}, char_width={estimated_char_width:.1f}, text_start_x={text_start_x:.1f}")

        for chord_elem in chord_elements:
            chord_text = chord_elem['text'].strip()
            if not chord_text:
                continue

            # Check if it's a valid chord
            chord_words = chord_text.split()
            for word in chord_words:
                if self._looks_like_chord(word):
                    # Calculate character position using font-based width
                    relative_x = chord_elem['x'] - text_start_x
                    char_position = int(relative_x / estimated_char_width)

                    # Ensure position is within text bounds
                    char_position = max(0, min(char_position, len(full_text)))

                    chords.append(ChordPosition(
                        chord=word,
                        position=char_position,
                        end_position=char_position + len(word),
                        x_coord=chord_elem['x']
                    ))
                    print(f"      🎸 Chord '{word}' at char position {char_position} (x={chord_elem['x']:.1f})")

        return sorted(chords, key=lambda x: x.position)

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

def main():
    parser = argparse.ArgumentParser(description='Parse single-column PDFs with PyMuPDF')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output name for display')

    args = parser.parse_args()

    pdf_parser = PyMuPDFParser()

    # Parse the song
    song = pdf_parser.parse_multi_page_pdf(args.input, args.output or "Parsed Song")

    print(f"\n✅ PyMuPDF Parser Results:")
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
