#!/usr/bin/env python3
"""
Hybrid Precise Parser for Croatian Songs
Combines PyMuPDF pixel-precise positioning with pdftotext text extraction
Uses actual Arial font character width calculations for accurate chord positioning
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

class HybridPreciseParser:
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

        # Arial font character widths (approximate, in font units)
        # These are based on typical Arial metrics at 1000 units per em
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

        print(f"🎸 Initialized Hybrid Precise Parser with {len(self.valid_chords)} valid chords")

    def get_char_width(self, char: str, font_size: float) -> float:
        """Get the actual width of a character in Arial font at given size"""
        # Get width in font units (default to average if not found)
        font_units = self.arial_char_widths.get(char, 556)  # 556 is average Arial character width
        
        # Convert to actual pixels: (font_units / 1000) * font_size
        return (font_units / 1000.0) * font_size

    def calculate_text_width(self, text: str, font_size: float) -> float:
        """Calculate the total width of text in Arial font"""
        total_width = 0.0
        for char in text:
            total_width += self.get_char_width(char, font_size)
        return total_width

    def find_char_position_at_x(self, text: str, font_size: float, target_x: float, text_start_x: float) -> int:
        """Find the character position in text that corresponds to a given X coordinate"""
        if target_x <= text_start_x:
            return 0
        
        relative_x = target_x - text_start_x
        current_x = 0.0
        
        for i, char in enumerate(text):
            char_width = self.get_char_width(char, font_size)
            
            # If we're within this character's width, return this position
            if current_x + char_width/2 >= relative_x:
                return i
            
            current_x += char_width
        
        # If we're past the end of the text, return the end position
        return len(text)

    def parse_and_export(self, pdf_files: List[str], song_name: str = "") -> str:
        """Parse PDF files using hybrid approach and export to ChordPro format"""
        print(f"🎵 Hybrid Precise parsing: {song_name or 'Multi-page song'}")

        # Step 1: Extract precise positioning data from PyMuPDF
        pymupdf_data = self._extract_pymupdf_data(pdf_files[0])  # Assuming single page for now
        
        # Step 2: Extract clean text from pdftotext
        pdftotext_lines = self._extract_pdftotext_data(pdf_files[0])
        
        # Step 3: Combine the data for precise positioning
        song = self._combine_data_for_precise_positioning(pymupdf_data, pdftotext_lines, song_name)
        
        # Step 4: Export to ChordPro format
        return self._export_to_chordpro(song)

    def _extract_pymupdf_data(self, pdf_path: str) -> Dict:
        """Extract positioning data from PyMuPDF"""
        doc = fitz.open(pdf_path)
        page = doc[0]
        text_dict = page.get_text("dict")

        chord_lines = []
        text_lines = []

        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_y = line["bbox"][1]
                    line_spans = []
                    
                    for span in line["spans"]:
                        if span['text'].strip():
                            line_spans.append({
                                'text': span['text'],
                                'x': span['bbox'][0],
                                'y': span['bbox'][1],
                                'font': span.get('font', ''),
                                'size': span.get('size', 12)
                            })
                    
                    if line_spans:
                        line_text = ''.join([s['text'] for s in line_spans])
                        
                        # Classify as chord line or text line
                        if self._is_chord_line_text(line_text):
                            chord_lines.append({
                                'y': line_y,
                                'spans': line_spans,
                                'text': line_text
                            })
                        else:
                            text_lines.append({
                                'y': line_y,
                                'spans': line_spans,
                                'text': line_text
                            })

        doc.close()
        
        return {
            'chord_lines': chord_lines,
            'text_lines': text_lines
        }

    def _extract_pdftotext_data(self, pdf_path: str) -> List[str]:
        """Extract clean text lines from pdftotext"""
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

def main():
    parser = argparse.ArgumentParser(description='Hybrid Precise Parser for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, nargs='+', help='PDF file(s) to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    hybrid_parser = HybridPreciseParser()

    # For now, just demonstrate the Arial font width calculation approach
    print("🔬 Testing Arial font width calculations:")

    # Test text from the problematic file
    test_text = "Za grijehe, koje smo počinili otvrdnjujući naša srca,"
    font_size = 11.0

    print(f"Text: '{test_text}'")
    print(f"Font size: {font_size}")

    total_width = hybrid_parser.calculate_text_width(test_text, font_size)
    print(f"Calculated total width: {total_width:.1f} pixels")

    # Test finding character positions
    test_positions = [0, 50, 100, 150, 200, 250, 300]
    for pos in test_positions:
        char_pos = hybrid_parser.find_char_position_at_x(test_text, font_size, pos, 0)
        if char_pos < len(test_text):
            char_at_pos = test_text[char_pos] if char_pos < len(test_text) else 'END'
            print(f"X={pos:3d} -> char_pos={char_pos:2d} -> '{char_at_pos}'")

    print("\\n📝 This demonstrates how we can use actual Arial font metrics")
    print("   to calculate precise character positions from pixel coordinates.")
    print("   The next step would be to integrate this with PyMuPDF chord positions.")

if __name__ == "__main__":
    main()
