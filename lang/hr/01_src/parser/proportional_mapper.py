#!/usr/bin/env python3
"""
Proportional Mapper - The Final Solution
Uses visual proportional mapping to accurately position chords
Based on the insight that chord positions should be proportionally mapped to text positions
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

class ProportionalMapper:
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

        print(f"🎸 Initialized Proportional Mapper with {len(self.valid_chords)} valid chords")

    def map_chords_proportionally(self, chord_line: str, text_line: str) -> List[ChordPosition]:
        """Map chords proportionally based on visual layout"""
        chords = []
        
        # Extract text content (after role marker)
        role_marker = self._extract_role_marker(text_line)
        text_content = text_line[len(role_marker):].strip() if role_marker else text_line.strip()
        
        print(f"      📝 Text: '{text_content}' (length: {len(text_content)})")
        print(f"      🎼 Chord line: '{chord_line}' (length: {len(chord_line)})")
        
        # Find the effective chord line length (trim trailing spaces)
        effective_chord_length = len(chord_line.rstrip())
        
        print(f"      📏 Effective chord line length: {effective_chord_length}")
        
        # Parse chords from chord line
        chord_positions = []
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
                chord_positions.append((chord_word, chord_start))
                print(f"      🎸 Found chord '{chord_word}' at pdftotext position {chord_start}")
        
        # Map each chord position proportionally to text position
        for chord_word, chord_pos in chord_positions:
            # Calculate proportional position
            if effective_chord_length > 0:
                proportion = chord_pos / effective_chord_length
                text_position = int(proportion * len(text_content))
                
                # Ensure position is within bounds
                text_position = max(0, min(text_position, len(text_content)))
                
                chords.append(ChordPosition(
                    chord=chord_word,
                    position=text_position
                ))
                
                char_at_pos = text_content[text_position] if text_position < len(text_content) else 'END'
                print(f"      🎯 Chord '{chord_word}': {chord_pos}/{effective_chord_length} = {proportion:.3f} -> pos {text_position} ('{char_at_pos}')")
            else:
                # Fallback: place at beginning
                chords.append(ChordPosition(
                    chord=chord_word,
                    position=0
                ))
        
        return sorted(chords, key=lambda x: x.position)

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files using proportional mapping and export to ChordPro format"""
        print(f"🎵 Proportional Mapping parsing: {song_name or 'Multi-page song'}")

        # Extract text using pdftotext
        pdftotext_lines = self._extract_pdftotext_data(pdf_files[0])
        
        # Parse using proportional mapping
        song = self._parse_with_proportional_mapping(pdftotext_lines, song_name)
        
        # Export to ChordPro format
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

    def _parse_with_proportional_mapping(self, pdftotext_lines: List[str], song_name: str) -> Song:
        """Parse using proportional mapping approach"""
        
        # Parse pdftotext lines for structure
        title, content_lines = self._detect_title_from_pdftotext(pdftotext_lines)
        if not title:
            title = song_name or "Untitled Song"

        kapodaster, content_lines = self._detect_kapodaster_from_pdftotext(content_lines)
        
        # Parse verses with proportional mapping
        verses, comments = self._parse_verses_with_proportional_mapping(content_lines)

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

    def _parse_verses_with_proportional_mapping(self, pdftotext_lines: List[str]) -> Tuple[List[Verse], List[str]]:
        """Parse verses using proportional mapping approach"""
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

                # Find chords using proportional mapping
                chords = self._find_chords_with_proportional_mapping(pdftotext_lines, i)

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
                    # Find chords using proportional mapping
                    chords = self._find_chords_with_proportional_mapping(pdftotext_lines, i)

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

    def _find_chords_with_proportional_mapping(self, pdftotext_lines: List[str], current_index: int) -> List[ChordPosition]:
        """Find chords using proportional mapping approach"""

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

        # Apply proportional mapping
        return self.map_chords_proportionally(chord_line, text_line)

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
        """Position chords within lyric text using proportional positions"""
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
    parser = argparse.ArgumentParser(description='Proportional Mapper for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    proportional_mapper = ProportionalMapper()

    # Parse and export
    chordpro_content = proportional_mapper.parse_and_export(args.input, args.song_name or "")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {args.output}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
