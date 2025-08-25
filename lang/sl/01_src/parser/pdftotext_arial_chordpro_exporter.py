#!/usr/bin/env python3
"""
Arial-aware ChordPro Exporter for Phase 3
Uses the Arial-aware pdftotext parser for accurate chord positioning
"""

from pdftotext_arial_parser import PDFToTextArialParser, Song, ChordPosition
from typing import List
import argparse

class PDFToTextArialChordProExporter:
    def __init__(self):
        self.parser = PDFToTextArialParser()

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files and export to ChordPro format using Arial-aware positioning"""
        
        # Parse the song using Arial-aware parser
        song = self.parser.parse_multi_page_pdf(pdf_files, song_name)
        
        # Export to ChordPro format
        return self._export_to_chordpro(song)

    def _export_to_chordpro(self, song: Song) -> str:
        """Export song to ChordPro format with precise Arial-based chord positioning"""
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
                    # Insert chords into text at precise Arial-calculated positions
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
        """Position chords within lyric text based on Arial font positioning"""
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
            
            # Use the Arial-calculated position directly
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
    parser = argparse.ArgumentParser(description='Export PDFs to ChordPro using Arial-aware pdftotext')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    exporter = PDFToTextArialChordProExporter()

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
