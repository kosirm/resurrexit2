#!/usr/bin/env python3
"""
ReadIris Pixel-Perfect Parser
Uses ReadIris OCR files with PyMuPDF for character-level precision chord positioning
This should be the final solution to the proportional font spacing problem
"""

import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import argparse

@dataclass
class CharacterSpan:
    text: str
    x_start: float
    x_end: float
    y: float

@dataclass
class ChordPosition:
    chord: str
    position: int
    x_coord: float

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

class ReadIrisPixelParser:
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

        print(f"🎸 Initialized ReadIris Pixel Parser with {len(self.valid_chords)} valid chords")

    def parse_and_export(self, readiris_pdf_path: str, song_name: str = "") -> str:
        """Parse ReadIris OCR PDF using pixel-perfect positioning and export to ChordPro format"""
        print(f"🎵 ReadIris Pixel-Perfect parsing: {song_name or Path(readiris_pdf_path).stem}")

        # Extract all character and chord data with pixel precision
        parsed_data = self._extract_readiris_data(readiris_pdf_path)
        
        # Parse into song structure using pixel-perfect positioning
        song = self._parse_with_pixel_precision(parsed_data, song_name)
        
        # Export to ChordPro format
        return self._export_to_chordpro(song)

    def _extract_readiris_data(self, pdf_path: str) -> Dict:
        """Extract character-level data from ReadIris OCR PDF"""
        doc = fitz.open(pdf_path)
        page = doc[0]
        text_dict = page.get_text("dict")

        lines_by_y = {}  # Group by Y coordinate
        chord_lines = []  # Store chord lines separately
        text_lines = []   # Store text lines separately

        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_y = round(line["bbox"][1])
                    
                    # Extract character spans from this line
                    character_spans = []
                    line_text = ""
                    
                    for span in line["spans"]:
                        if span['text'].strip():
                            char_span = CharacterSpan(
                                text=span['text'],
                                x_start=span['bbox'][0],
                                x_end=span['bbox'][2],
                                y=span['bbox'][1]
                            )
                            character_spans.append(char_span)
                            line_text += span['text']
                    
                    if character_spans:
                        line_data = {
                            'y': line_y,
                            'text': line_text.strip(),
                            'character_spans': character_spans,
                            'bbox': line["bbox"]
                        }
                        
                        # Classify as chord line or text line
                        if self._is_chord_line_text(line_text):
                            chord_lines.append(line_data)
                            print(f"🎼 Chord line at Y={line_y}: '{line_text.strip()}'")
                        else:
                            text_lines.append(line_data)
                            print(f"📝 Text line at Y={line_y}: '{line_text.strip()}'")
                        
                        lines_by_y[line_y] = line_data

        doc.close()
        
        return {
            'lines_by_y': lines_by_y,
            'chord_lines': chord_lines,
            'text_lines': text_lines,
            'sorted_y_positions': sorted(lines_by_y.keys())
        }

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

    def _parse_with_pixel_precision(self, parsed_data: Dict, song_name: str) -> Song:
        """Parse using pixel-perfect positioning"""
        
        text_lines = parsed_data['text_lines']
        chord_lines = parsed_data['chord_lines']
        
        # Detect title
        title = self._detect_title_from_lines(text_lines)
        if not title:
            title = song_name or "Untitled Song"

        # Detect kapodaster
        kapodaster = self._detect_kapodaster_from_lines(text_lines)
        
        # Parse verses with pixel-perfect chord positioning
        verses, comments = self._parse_verses_with_pixel_precision(text_lines, chord_lines)

        return Song(title=title, kapodaster=kapodaster, verses=verses, comments=comments)

    def _detect_title_from_lines(self, text_lines: List[Dict]) -> str:
        """Detect title from text lines"""
        for line_data in text_lines[:10]:  # Check first 10 lines
            text = line_data['text']
            
            if not text.strip():
                continue

            # Skip Kapodaster lines
            if 'kapodaster' in text.lower() or 'kapo' in text.lower():
                continue

            # Look for title - uppercase, reasonable length, no role markers
            if (text.strip().isupper() and
                len(text.strip()) > 10 and
                not any(role in text for role in self.role_markers)):

                print(f"📋 TITLE: '{text.strip()}'")
                return text.strip()

        return ""

    def _detect_kapodaster_from_lines(self, text_lines: List[Dict]) -> str:
        """Detect Kapodaster from text lines"""
        for line_data in text_lines[:5]:  # Check first 5 lines
            text = line_data['text']
            
            if not text.strip():
                continue

            if 'kapodaster' in text.lower() or 'kapo' in text.lower():
                print(f"🎸 KAPODASTER: '{text.strip()}'")
                return text.strip()

        return ""

    def _parse_verses_with_pixel_precision(self, text_lines: List[Dict], chord_lines: List[Dict]) -> Tuple[List[Verse], List[str]]:
        """Parse verses using pixel-perfect chord positioning"""
        verses = []
        comments = []
        current_verse_lines = []
        current_role = ""

        for text_line_data in text_lines:
            text = text_line_data['text']
            
            if not text.strip():
                continue

            # Check for comment
            if self._is_comment_line(text):
                comments.append(text.strip())
                print(f"💬 COMMENT: '{text.strip()}'")
                continue

            # Check for role marker
            role_marker = self._extract_role_marker(text)

            if role_marker:
                # Save previous verse if exists
                if current_verse_lines and current_role:
                    verses.append(Verse(role=current_role, lines=current_verse_lines))
                    print(f"🎭 Completed verse: {current_role} with {len(current_verse_lines)} lines")

                # Start new verse
                current_role = role_marker
                text_after_role = text[len(role_marker):].strip()

                # Find pixel-perfect chord positions
                chords = self._find_pixel_perfect_chords(text_line_data, chord_lines)

                verse_line = VerseLine(
                    text=text_after_role,
                    chords=chords,
                    original_line=text
                )
                current_verse_lines = [verse_line]
                print(f"🎵 Started verse: {current_role}")

            elif current_role:
                # Continuation line in current verse
                if not self._is_chord_line_text(text):
                    # Find pixel-perfect chord positions
                    chords = self._find_pixel_perfect_chords(text_line_data, chord_lines)

                    verse_line = VerseLine(
                        text=text.strip(),
                        chords=chords,
                        original_line=text
                    )
                    current_verse_lines.append(verse_line)

        # Add final verse
        if current_verse_lines and current_role:
            verses.append(Verse(role=current_role, lines=current_verse_lines))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines")

        return verses, comments

    def _find_pixel_perfect_chords(self, text_line_data: Dict, chord_lines: List[Dict]) -> List[ChordPosition]:
        """Find chords using pixel-perfect positioning from ReadIris OCR"""
        chords = []

        text_y = text_line_data['y']
        text_character_spans = text_line_data['character_spans']

        # Find the chord line that's closest above this text line
        best_chord_line = None
        min_distance = float('inf')

        for chord_line_data in chord_lines:
            chord_y = chord_line_data['y']

            # Only consider chord lines above the text line
            if chord_y < text_y:
                distance = text_y - chord_y
                if distance < min_distance:
                    min_distance = distance
                    best_chord_line = chord_line_data

        if not best_chord_line:
            print(f"      ❌ No chord line found above text at Y={text_y}")
            return chords

        print(f"      🔍 Found chord line at Y={best_chord_line['y']} above text at Y={text_y}")
        print(f"      🎼 Chord line: '{best_chord_line['text']}'")

        # Extract individual chords from the chord line
        chord_spans = []
        for span in best_chord_line['character_spans']:
            chord_text = span.text.strip()
            if chord_text and self._looks_like_chord(chord_text):
                chord_spans.append({
                    'chord': chord_text,
                    'x': span.x_start,
                    'x_center': (span.x_start + span.x_end) / 2
                })
                print(f"      🎸 Found chord '{chord_text}' at X={span.x_start:.1f}")

        # Now map each chord to the closest character in the text line
        role_marker = self._extract_role_marker(text_line_data['text'])
        text_content = text_line_data['text'][len(role_marker):].strip() if role_marker else text_line_data['text'].strip()

        print(f"      📝 Text content: '{text_content}'")

        # Build character position map from text spans
        char_positions = []
        char_index = 0

        for span in text_character_spans:
            span_text = span.text

            # Skip role marker characters
            if role_marker and char_index < len(role_marker):
                chars_to_skip = min(len(span_text), len(role_marker) - char_index)
                span_text = span_text[chars_to_skip:]
                char_index += chars_to_skip

                if not span_text:
                    continue

            # Calculate character positions within this span
            span_width = span.x_end - span.x_start
            char_width = span_width / len(span_text) if len(span_text) > 0 else 0

            for i, char in enumerate(span_text):
                char_x = span.x_start + (i * char_width)
                char_positions.append({
                    'char': char,
                    'x': char_x,
                    'text_index': len(char_positions)  # Position in final text
                })

        print(f"      📍 Built {len(char_positions)} character positions")

        # Map each chord to the closest character
        for chord_data in chord_spans:
            chord_x = chord_data['x_center']
            chord_name = chord_data['chord']

            # Find the closest character
            best_char_pos = 0
            min_distance = float('inf')

            for i, char_data in enumerate(char_positions):
                distance = abs(chord_x - char_data['x'])
                if distance < min_distance:
                    min_distance = distance
                    best_char_pos = i

            if best_char_pos < len(char_positions):
                char_at_pos = char_positions[best_char_pos]['char']
                print(f"      🎯 Chord '{chord_name}' at X={chord_x:.1f} -> char_pos={best_char_pos} ('{char_at_pos}')")

                chords.append(ChordPosition(
                    chord=chord_name,
                    position=best_char_pos,
                    x_coord=chord_x
                ))
            else:
                print(f"      ⚠️ Chord '{chord_name}' could not be mapped to character")

        return sorted(chords, key=lambda x: x.position)

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
        """Position chords within lyric text using pixel-perfect positions"""
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
    parser = argparse.ArgumentParser(description='ReadIris Pixel-Perfect Parser for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, help='ReadIris OCR PDF file to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    readiris_parser = ReadIrisPixelParser()

    # Parse and export
    chordpro_content = readiris_parser.parse_and_export(args.input, args.song_name or "")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {args.output}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
