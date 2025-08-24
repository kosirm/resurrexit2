#!/usr/bin/env python3
"""
Phase 3 PDFtoText ChordPro Exporter
Converts PDFtoText parsed song data to ChordPro format with precise space-based chord positioning.
Leverages the superior positioning accuracy of pdftotext.
"""

import argparse
from pathlib import Path
from typing import List
from pdftotext_parser import PDFtoTextParser, Song, Verse, VerseLine, ChordPosition

class PDFtoTextChordProExporter:
    def __init__(self):
        self.parser = PDFtoTextParser()
    
    def export_to_chordpro(self, song: Song) -> str:
        """Convert song to ChordPro format with precise positioning"""
        chordpro_lines = []

        # Add title directive
        if song.title:
            chordpro_lines.append(f"{{title: {song.title}}}")
            chordpro_lines.append("")

        # Add Kapodaster info if present (will be detected from song metadata)
        if hasattr(song, 'kapodaster') and song.kapodaster:
            chordpro_lines.append(f"{{comment: {song.kapodaster}}}")
            chordpro_lines.append("")
        
        # Process verses with role-based formatting
        for verse in song.verses:
            for i, line in enumerate(verse.lines):
                if line.chords:
                    # Use the original line to get proper chord positioning
                    # Then extract just the text part for ChordPro format
                    chordpro_line = self._position_chords_in_original_line(line.chords, line.original_line, verse.role if i == 0 else "")
                else:
                    chordpro_line = line.text

                # Add role prefix ONLY on first line of verse
                if i == 0:
                    chordpro_lines.append(f"{verse.role}\t{chordpro_line}")
                else:
                    chordpro_lines.append(f"\t{chordpro_line}")  # Just tab for continuation lines

            chordpro_lines.append("")  # Empty line between verses

        # Add comments at the end
        if hasattr(song, 'comments') and song.comments:
            for comment in song.comments:
                chordpro_lines.append(f"{{comment: {comment}}}")

        return '\n'.join(chordpro_lines)
    
    def _position_chords_in_lyrics(self, chords: List[ChordPosition], lyric_text: str, role_offset: int = 0) -> str:
        """Position chords within lyric text based on precise spacing (adapted from existing converter)"""
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

            # Adjust chord position by subtracting role marker offset
            adjusted_chord_pos = chord_pos - role_offset

            # Map chord position to lyric position (space-based precision)
            # This is the key advantage of pdftotext - direct character mapping
            target_lyric_pos = max(0, min(adjusted_chord_pos, len(lyric_text)))

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

    def _position_chords_in_original_line(self, chords: List[ChordPosition], original_line: str, role: str) -> str:
        """Position chords using smart heuristics to handle proportional font spacing"""
        if not chords:
            # Extract text after role marker
            if role and original_line.startswith(role):
                return original_line[len(role):].strip()
            return original_line.strip()

        # Extract just the text part
        text_start = 0
        if role and original_line.startswith(role):
            text_start = len(role)
            # Skip any whitespace after role marker
            while text_start < len(original_line) and original_line[text_start] in ' \t':
                text_start += 1

        text_part = original_line[text_start:].rstrip() if text_start < len(original_line) else ""

        if not text_part:
            return ""

        # Sort chords by position
        sorted_chords = sorted(chords, key=lambda x: x.position)

        # Use smart positioning based on proportional font heuristics
        result = ""
        last_pos = 0

        for chord in sorted_chords:
            chord_pos = chord.position

            # Smart mapping: try to find meaningful positions in the text
            target_pos = self._find_smart_chord_position(chord_pos, text_start, text_part, chord.chord)

            # Ensure we don't go backwards
            target_pos = max(target_pos, last_pos)
            target_pos = min(target_pos, len(text_part))

            # Add text up to this position
            if target_pos > last_pos:
                result += text_part[last_pos:target_pos]
                last_pos = target_pos

            # Add the chord
            result += f"[{chord.chord}]"

        # Add remaining text
        if last_pos < len(text_part):
            result += text_part[last_pos:]

        return result

    def _find_smart_chord_position(self, chord_pos: int, text_start: int, text_part: str, chord: str) -> int:
        """Find smart position for chord based on visual alignment heuristics"""
        # Convert absolute position to relative position
        relative_pos = chord_pos - text_start

        # If the relative position is reasonable, use it
        if 0 <= relative_pos <= len(text_part):
            return relative_pos

        # If position is before text start, place at beginning
        if relative_pos < 0:
            return 0

        # If position is beyond text, try to find a good spot
        if relative_pos > len(text_part):
            # Look for word boundaries near the end
            words = text_part.split()
            if len(words) >= 2:
                # Place before the last word
                last_word_start = text_part.rfind(words[-1])
                if last_word_start > 0:
                    return last_word_start

            # Fallback: place at the end
            return len(text_part)

        return relative_pos

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files and export to ChordPro format"""
        print(f"🎵 PDFtoText ChordPro Export: {song_name or 'Multi-page song'}")
        
        # Parse the song
        song = self.parser.parse_multi_page_pdf(pdf_files, song_name)
        
        # Export to ChordPro
        chordpro_content = self.export_to_chordpro(song)
        
        return chordpro_content

def main():
    parser = argparse.ArgumentParser(description='Export PDFs to ChordPro format using PDFtoText')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', required=True, help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for parsing')
    
    args = parser.parse_args()
    
    exporter = PDFtoTextChordProExporter()
    
    # Parse and export
    chordpro_content = exporter.parse_and_export(args.input, args.song_name or "")
    
    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(chordpro_content)
    
    print(f"\n✅ PDFtoText ChordPro Export Complete:")
    print(f"   📄 Output: {output_path}")
    print(f"   📊 Size: {len(chordpro_content)} characters")
    print(f"   🎸 Space-based precision positioning")
    
    # Show preview
    lines = chordpro_content.split('\n')
    print(f"\n📋 Preview (first 10 lines):")
    for i, line in enumerate(lines[:10]):
        print(f"   {i+1:2d}: {line}")
    
    if len(lines) > 10:
        print(f"   ... ({len(lines) - 10} more lines)")

if __name__ == "__main__":
    main()
