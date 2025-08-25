#!/usr/bin/env python3
"""
PyMuPDF-based ChordPro Exporter for Phase 3
Uses proven font-based character width calculation for accurate chord positioning
Based on the working ABBY solution approach
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

class PyMuPDFChordProExporter:
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

        print(f"🎸 Initialized PyMuPDF ChordPro exporter with {len(self.valid_chords)} valid chords")

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files and export to ChordPro format using PyMuPDF"""
        print(f"🎵 PyMuPDF ChordPro export: {song_name or 'Multi-page song'}")

        # Extract text elements with precise positioning
        all_elements = []
        for i, pdf_file in enumerate(pdf_files):
            print(f"📄 Processing page {i+1}: {Path(pdf_file).name}")
            elements = self._extract_text_elements(pdf_file)
            all_elements.extend(elements)

        print(f"📊 Total text elements: {len(all_elements)}")

        # Group elements into lines
        lines = self._group_elements_by_lines(all_elements)
        print(f"📊 Total lines: {len(lines)}")

        # Parse into song structure
        song = self._parse_lines_to_song(lines, song_name)

        # Export to ChordPro format
        return self._export_to_chordpro(song)

    def _extract_text_elements(self, pdf_path: str) -> List[Dict]:
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

    def _group_elements_by_lines(self, elements: List[Dict]) -> List[List[Dict]]:
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

            # If we find a chord line, extract chords from it using proven ABBY approach
            if self._is_chord_line_elements(line_elements):
                chords = self._position_chords_abby_style(line_elements, lines[current_index])
                print(f"      🔍 Found chord line above at index {j}: '{line_text}'")
                return chords

            # If we find a text line with role marker or other content, stop searching
            if (self._extract_role_marker(line_text) or
                (line_text and not self._is_chord_line_elements(line_elements) and not self._is_comment_line(line_text))):
                print(f"      🛑 Stopped chord search at text line: '{line_text}'")
                break

        return []

    def _position_chords_abby_style(self, chord_elements: List[Dict], text_elements: List[Dict]) -> List[ChordPosition]:
        """Position chords using the proven ABBY font-based approach"""
        chords = []

        if not text_elements or not chord_elements:
            return chords

        # Calculate actual text width using font metrics (ABBY approach)
        # Average character width for Times New Roman at typical sizes
        avg_font_size = sum(elem.get('size', 12) for elem in text_elements) / len(text_elements)
        estimated_char_width = avg_font_size * 0.5  # Times New Roman is about 0.5x font size per character

        # Get text line start position
        text_start_x = min(elem['x'] for elem in text_elements)

        # Combine all text to get the full text line
        full_text = ''.join([elem['text'] for elem in text_elements])

        print(f"      📏 Font analysis: avg_size={avg_font_size:.1f}, char_width={estimated_char_width:.1f}, text_start_x={text_start_x:.1f}")
        print(f"      📝 Text: '{full_text}'")

        for chord_elem in chord_elements:
            chord_text = chord_elem['text']
            if not chord_text.strip():
                continue

            print(f"      🎼 Processing chord span: '{chord_text}'")

            # Parse individual chords from the chord line using character positions
            # This handles the case where PyMuPDF gives us the entire chord line as one span
            chord_line_start_x = chord_elem['x']

            # Find individual chords and their positions within the chord line
            i = 0
            while i < len(chord_text):
                char = chord_text[i]

                # Skip spaces
                if char.isspace():
                    i += 1
                    continue

                # Found start of a potential chord
                chord_start = i
                chord_word = ""

                # Extract the chord word (non-space characters)
                while i < len(chord_text) and not chord_text[i].isspace():
                    chord_word += chord_text[i]
                    i += 1

                # Check if it's a valid chord
                if self._looks_like_chord(chord_word):
                    # Calculate position of this chord within the chord line
                    chord_char_pos_in_line = chord_start

                    # Calculate absolute X position of this chord
                    chord_x = chord_line_start_x + (chord_char_pos_in_line * estimated_char_width)

                    # Calculate relative position to text line
                    relative_x = chord_x - text_start_x
                    char_position = max(0, int(relative_x / estimated_char_width))
                    char_position = min(char_position, len(full_text))

                    chords.append(ChordPosition(
                        chord=chord_word,
                        position=char_position,
                        x_coord=chord_x
                    ))
                    print(f"      🎸 Chord '{chord_word}' at char_pos_in_chord_line={chord_char_pos_in_line}, calculated_x={chord_x:.1f}, relative_x={relative_x:.1f}, final_char_pos={char_position}")

        # Sort chords by position
        chords.sort(key=lambda c: c.position)
        return chords

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

    def _export_to_chordpro(self, song: Song) -> str:
        """Export song to ChordPro format with precise chord positioning"""
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

        # Process verses with role-based formatting
        for verse in song.verses:
            for i, line in enumerate(verse.lines):
                if line.chords:
                    # Insert chords into text at precise positions using ABBY-style positioning
                    chordpro_line = self._position_chords_in_lyrics(line.chords, line.text)
                else:
                    chordpro_line = line.text

                # Add role prefix ONLY on first line of verse
                if i == 0:
                    chordpro_lines.append(f"{verse.role}\t{chordpro_line}")
                else:
                    chordpro_lines.append(f"\t{chordpro_line}")  # Just tab for continuation lines

            chordpro_lines.append("")  # Empty line between verses

        return '\n'.join(chordpro_lines)

    def _position_chords_in_lyrics(self, chords: List[ChordPosition], lyric_text: str) -> str:
        """Position chords within lyric text based on precise font-based positioning"""
        if not chords or not lyric_text.strip():
            if chords:
                # Chord-only line
                chord_names = [c.chord for c in chords]
                return '[' + ']['.join(chord_names) + ']'
            else:
                # Lyric-only line
                return lyric_text

        # Create a mapping of chord positions to lyric positions
        result = ""
        lyric_pos = 0

        # Sort chords by position
        sorted_chords = sorted(chords, key=lambda x: x.position)

        for chord in sorted_chords:
            chord_pos = chord.position

            # Use the precise position calculated by font-based approach
            target_lyric_pos = min(chord_pos, len(lyric_text))

            # Add lyric text up to this position
            if target_lyric_pos > lyric_pos:
                result += lyric_text[lyric_pos:target_lyric_pos]
                lyric_pos = target_lyric_pos

            # Add the chord
            result += f"[{chord.chord}]"

        # Add remaining lyric text
        if lyric_pos < len(lyric_text):
            result += lyric_text[lyric_pos:]

        return result

def main():
    parser = argparse.ArgumentParser(description='Export PDFs to ChordPro using PyMuPDF')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    exporter = PyMuPDFChordProExporter()

    # Parse and export
    chordpro_content = exporter.parse_and_export(args.input, args.song_name or "")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {args.output}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
