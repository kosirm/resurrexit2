#!/usr/bin/env python3
"""
PyMuPDF Span-Based Parser
Uses exact span coordinates from PyMuPDF for precise chord positioning
This should be the most accurate approach using span-to-span pixel mapping
"""

import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import argparse

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

class PyMuPDFSpanParser:
    def __init__(self):
        self.role_markers = ['K.+Z.', 'K.+P.', 'K.', 'Z.', 'P.', 'D.']
        
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

        print(f"🎸 Initialized PyMuPDF Span Parser with {len(self.valid_chords)} valid chords")

    def get_char_width(self, char: str, font_size: float) -> float:
        """Get the actual width of a character in Arial font at given size"""
        font_units = self.arial_char_widths.get(char, 556)  # 556 is average Arial character width
        return (font_units / 1000.0) * font_size

    def find_chord_positions_in_span(self, chord_span_text: str, chord_span_start: float, chord_span_width: float) -> List[Tuple[str, float]]:
        """Find individual chord positions within the chord span"""
        chord_positions = []
        
        # Parse chords from the span text
        words = chord_span_text.split()
        current_pos = 0
        
        for word in words:
            if self._looks_like_chord(word):
                # Find the position of this word in the original text
                word_start_in_text = chord_span_text.find(word, current_pos)
                if word_start_in_text != -1:
                    # Calculate proportional position within the span
                    proportional_pos = word_start_in_text / len(chord_span_text)
                    pixel_pos = chord_span_start + (proportional_pos * chord_span_width)
                    
                    chord_positions.append((word, pixel_pos))
                    print(f"      🎸 Found chord '{word}' at text_pos={word_start_in_text}, pixel_x={pixel_pos:.1f}")
                    
                    current_pos = word_start_in_text + len(word)
        
        return chord_positions

    def map_chord_to_verse_position(self, chord_pixel_x: float, chord_span_start: float, chord_span_width: float,
                                   verse_text: str, verse_span_start: float, verse_span_width: float, font_size: float) -> int:
        """Map chord pixel position to verse character position using direct pixel mapping"""

        # FIXED: Map chord position directly to verse span, not via chord span proportions
        # Calculate proportional position of chord within the verse span
        if verse_span_width == 0:
            return 0

        # Clamp chord position to verse span boundaries
        chord_x_clamped = max(verse_span_start, min(chord_pixel_x, verse_span_start + verse_span_width))

        # Calculate proportional position within verse span
        proportional_pos = (chord_x_clamped - verse_span_start) / verse_span_width

        # The target pixel position is the clamped chord position
        verse_pixel_x = chord_x_clamped

        print(f"      🎯 Chord at x={chord_pixel_x:.1f} -> clamped_x={chord_x_clamped:.1f} -> proportion={proportional_pos:.3f}")

        # Convert verse pixel position to character position using Arial font metrics
        current_pixel = verse_span_start
        char_position = 0

        for i, char in enumerate(verse_text):
            char_width = self.get_char_width(char, font_size)
            char_center = current_pixel + (char_width / 2)

            if verse_pixel_x <= char_center:
                char_position = i
                break

            current_pixel += char_width
            char_position = i + 1

        # Ensure position is within bounds
        char_position = max(0, min(char_position, len(verse_text)))

        char_at_pos = verse_text[char_position] if char_position < len(verse_text) else 'END'
        print(f"      📍 Mapped to char_pos={char_position} ('{char_at_pos}')")

        return char_position

    def parse_and_export(self, pdf_path: str, song_name: str = "") -> str:
        """Parse PDF using PyMuPDF span-based approach and export to ChordPro format"""
        print(f"🎵 PyMuPDF Span-based parsing: {song_name or Path(pdf_path).stem}")

        # Extract span data from PyMuPDF
        span_data = self._extract_span_data(pdf_path)
        
        # Parse into song structure using span-based positioning
        song = self._parse_with_span_positioning(span_data, song_name)
        
        # Export to ChordPro format
        return self._export_to_chordpro(song)

    def _extract_span_data(self, pdf_path: str) -> Dict:
        """Extract span data from PyMuPDF with color and font analysis for robust classification - supports multi-page"""
        doc = fitz.open(pdf_path)

        chord_lines = []
        text_lines = []
        title_lines = []
        kapodaster_lines = []
        comment_lines = []

        print(f"📄 Processing {len(doc)} page(s)")

        # Process all pages
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")

            print(f"📄 Processing page {page_num + 1}/{len(doc)}")

            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ''.join([span['text'] for span in line['spans']])

                        if not line_text.strip():
                            continue

                        # Get the main span for analysis
                        main_span = line['spans'][0] if line['spans'] else None
                        if not main_span:
                            continue

                        # Extract color and font information
                        color = main_span.get('color', 0)  # 0 = black, other values = colors
                        font_size = main_span.get('size', 11.0)
                        font_name = main_span.get('font', '')

                        # Convert color to RGB for analysis (pink detection)
                        is_pink = self._is_pink_color(color)

                        # Adjust Y coordinate for multi-page (add page offset)
                        page_height = page.rect.height
                        adjusted_y = line['bbox'][1] + (page_num * page_height)

                        line_data = {
                            'text': line_text,
                            'text_content': line_text.strip(),
                            'x_start': main_span['bbox'][0],
                            'x_end': main_span['bbox'][2],
                            'width': main_span['bbox'][2] - main_span['bbox'][0],
                            'y': adjusted_y,  # Use adjusted Y coordinate
                            'original_y': line['bbox'][1],  # Keep original for reference
                            'page_num': page_num,
                            'font_size': font_size,
                            'color': color,
                            'is_pink': is_pink,
                            'font_name': font_name
                        }

                        # Classify the line based on content, color, and font
                        if self._is_chord_line_text(line_text):
                            # Chord line - but we need to handle multi-span chord lines
                            # Store individual spans for later combination
                            chord_line_data = line_data.copy()
                            chord_line_data['spans'] = line['spans']  # Keep all spans for multi-span chord lines
                            chord_lines.append(chord_line_data)
                            print(f"🎼 Chord line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")

                        elif self._is_title_line(line_text, font_size, is_pink):
                            # Title line - pink, uppercase, larger font
                            title_lines.append(line_data)
                            print(f"📋 Title line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")

                        elif self._is_kapodaster_line(line_text, is_pink):
                            # Kapodaster line - pink, contains "kapodaster"
                            kapodaster_lines.append(line_data)
                            print(f"🎸 Kapodaster line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")

                        elif self._is_comment_line_enhanced(line_text, is_pink):
                            # Check if this is an inline comment (pink, in parentheses, complete)
                            if (is_pink and
                                line_text.strip().startswith('(') and
                                line_text.strip().endswith(')')):
                                # Inline comment - treat as text line to preserve position
                                text_lines.append(line_data)
                                print(f"💬 Inline comment (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")
                            else:
                                # Regular comment - collect separately
                                comment_lines.append(line_data)
                                print(f"💬 Comment line (page {page_num + 1}): '{line_text.strip()}' (pink: {is_pink}, size: {font_size:.1f})")

                        else:
                            # Regular text line (verses, role markers)
                            # Handle role markers and text content
                            has_role_marker = any(role in line_text for role in self.role_markers)

                            if has_role_marker:
                                # Extract text content after role marker
                                for role in sorted(self.role_markers, key=len, reverse=True):
                                    if line_text.strip().startswith(role):
                                        text_after_role = line_text[len(role):].strip()
                                        if text_after_role:
                                            line_data['text_content'] = text_after_role
                                        break

                            text_lines.append(line_data)
                            role_info = " (with role)" if has_role_marker else ""
                            print(f"📝 Text line{role_info} (page {page_num + 1}): '{line_text.strip()[:50]}...' (size: {font_size:.1f})")

        doc.close()

        # Combine chord lines that are on the same Y position
        combined_chord_lines = self._combine_chord_lines_by_y_position(chord_lines)

        return {
            'chord_lines': combined_chord_lines,
            'text_lines': text_lines,
            'title_lines': title_lines,
            'kapodaster_lines': kapodaster_lines,
            'comment_lines': comment_lines
        }

    def _combine_chord_lines_by_y_position(self, chord_lines: List[Dict]) -> List[Dict]:
        """Combine chord lines that are on the same Y position into single chord lines"""
        if not chord_lines:
            return []

        # Group chord lines by Y position (with small tolerance for floating point differences)
        y_groups = {}
        for chord_line in chord_lines:
            y_pos = chord_line['y']

            # Find existing group with similar Y position (within 1 pixel tolerance)
            found_group = None
            for existing_y in y_groups.keys():
                if abs(y_pos - existing_y) < 1.0:
                    found_group = existing_y
                    break

            if found_group is not None:
                y_groups[found_group].append(chord_line)
            else:
                y_groups[y_pos] = [chord_line]

        # Combine chord lines in each Y group
        combined_lines = []
        for y_pos, group_lines in y_groups.items():
            if len(group_lines) == 1:
                # Single chord line, use as-is
                combined_lines.append(group_lines[0])
                print(f"🎼 Single chord line at Y={y_pos:.1f}: '{group_lines[0]['text'].strip()}'")
            else:
                # Multiple chord lines at same Y position - combine them
                combined_line = self._merge_chord_lines_at_same_y(group_lines, y_pos)
                combined_lines.append(combined_line)
                print(f"🎼 Combined chord line at Y={y_pos:.1f}: '{combined_line['text'].strip()}'")

        return combined_lines

    def _merge_chord_lines_at_same_y(self, chord_lines: List[Dict], y_pos: float) -> Dict:
        """Merge multiple chord lines at the same Y position into a single chord line"""
        # Sort by X position
        sorted_lines = sorted(chord_lines, key=lambda x: x['x_start'])

        # Find the overall bounding box
        min_x = min(line['x_start'] for line in sorted_lines)
        max_x = max(line['x_end'] for line in sorted_lines)

        # Create combined text by positioning each chord at its correct X position
        combined_text = ""
        current_x = min_x

        for line in sorted_lines:
            # Add spaces to reach the chord position
            spaces_needed = max(0, int((line['x_start'] - current_x) / 6))  # Approximate character width
            combined_text += " " * spaces_needed
            combined_text += line['text'].strip()
            current_x = line['x_end']

        # Create the combined chord line data
        return {
            'text': combined_text,
            'text_content': combined_text.strip(),
            'x_start': min_x,
            'x_end': max_x,
            'width': max_x - min_x,
            'y': y_pos,
            'font_size': sorted_lines[0]['font_size'],
            'color': sorted_lines[0]['color'],
            'is_pink': sorted_lines[0]['is_pink'],
            'font_name': sorted_lines[0]['font_name'],
            'spans': [span for line in sorted_lines for span in line.get('spans', [])]
        }

    def _is_pink_color(self, color: int) -> bool:
        """Check if color is pink/magenta (used for titles, kapodaster, comments)"""
        # Pink/magenta colors in Croatian songbook PDFs
        # Based on analysis: 15466636 is the pink color used for titles, chords, etc.
        pink_colors = {
            15466636,  # Main pink color used in Croatian songbooks
            15466637,  # Slight variation
            15466635,  # Slight variation
        }
        return color in pink_colors

    def _is_title_line(self, text: str, font_size: float, is_pink: bool) -> bool:
        """Check if line is a title based on content, font size, and color"""
        text_clean = text.strip()

        # Enhanced title detection for Croatian songs
        import re

        # Remove biblical references and parentheses content for uppercase check
        # Common patterns: "- Ps 64 (65)", "- Mt 5,1-12", "(Kroz godinu)", etc.
        text_for_case_check = re.sub(r'\s*-\s*[A-Z][a-z]+\s*\d+[^)]*(\([^)]*\))?', '', text_clean)
        text_for_case_check = re.sub(r'\([^)]*\)', '', text_for_case_check).strip()

        # Check if the main part (without biblical refs) is mostly uppercase
        # Allow some lowercase letters for prepositions, conjunctions, etc.
        if text_for_case_check:
            uppercase_chars = sum(1 for c in text_for_case_check if c.isupper())
            lowercase_chars = sum(1 for c in text_for_case_check if c.islower())
            total_letters = uppercase_chars + lowercase_chars

            if total_letters > 0:
                uppercase_ratio = uppercase_chars / total_letters
                is_mostly_uppercase = uppercase_ratio >= 0.7  # At least 70% uppercase
            else:
                is_mostly_uppercase = True  # No letters, consider as valid
        else:
            is_mostly_uppercase = text_clean.isupper()

        # Title criteria: mostly uppercase, reasonable length, larger font, pink color preferred
        return (is_mostly_uppercase and
                len(text_clean) > 4 and  # Reduced from 8 to 4 for short titles like "TE DEUM", "DUHOVI"
                font_size >= 12.0 and  # Larger or equal font
                is_pink and  # Pink color is required for titles
                not any(role in text_clean for role in self.role_markers) and
                not self._is_chord_line_text(text_clean) and
                'kapodaster' not in text_clean.lower())

    def _is_kapodaster_line(self, text: str, is_pink: bool) -> bool:
        """Check if line is kapodaster based on content and color"""
        text_lower = text.strip().lower()
        return (is_pink and
                ('kapodaster' in text_lower or 'kapo' in text_lower))

    def _is_comment_line_enhanced(self, text: str, is_pink: bool) -> bool:
        """Enhanced comment detection based on content and color"""
        text_clean = text.strip()

        # Type 1: Pink with parentheses (including inline comments)
        # Simple rule: pink text in parentheses = comment (inline or regular)
        if (is_pink and
            text_clean.startswith('(') and
            text_clean.endswith(')')):
            return True

        # Type 1b: Continuation of parentheses comment (starts with "bez:" or ends with ")")
        # FIXED: Be more specific to avoid catching titles like "SVET (Kroz godinu)"
        if text_clean.startswith('bez:'):
            return True

        # Only catch ending ')' if it's clearly a continuation comment, not a title
        if (text_clean.endswith(')') and
            'blagoslovljen' in text_clean.lower() and
            not text_clean.startswith('SVET')):
            return True

        # Type 2: Starts with * or ** (usually under horizontal line)
        if text_clean.startswith('*') and ('zbor' in text_clean.lower() or 'odgovara' in text_clean.lower()):
            return True

        return False

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

    def _parse_with_span_positioning(self, span_data: Dict, song_name: str) -> Song:
        """Parse using span-based positioning with enhanced classification"""

        chord_lines = span_data['chord_lines']
        text_lines = span_data['text_lines']
        title_lines = span_data['title_lines']
        kapodaster_lines = span_data['kapodaster_lines']
        comment_lines = span_data['comment_lines']

        # Extract title from title lines (should be at the top)
        title = self._extract_title_from_classified_lines(title_lines, song_name)

        # Extract kapodaster from kapodaster lines
        kapodaster = self._extract_kapodaster_from_classified_lines(kapodaster_lines)

        # Extract comments from comment lines (should be at the bottom)
        comments = self._extract_comments_from_classified_lines(comment_lines)

        # Parse verses with span-based chord positioning (only from text_lines)
        verses = self._parse_verses_with_span_positioning_enhanced(text_lines, chord_lines)

        return Song(title=title, kapodaster=kapodaster, verses=verses, comments=comments)

    def _extract_title_from_classified_lines(self, title_lines: List[Dict], song_name: str) -> str:
        """Extract title from classified title lines"""
        if not title_lines:
            return song_name or "Untitled Song"

        # Sort by Y coordinate (top to bottom) and take the first (topmost) title
        title_lines_sorted = sorted(title_lines, key=lambda x: x['y'])
        title = title_lines_sorted[0]['text'].strip()

        print(f"📋 TITLE (from classification): '{title}'")
        return title

    def _extract_kapodaster_from_classified_lines(self, kapodaster_lines: List[Dict]) -> str:
        """Extract kapodaster from classified kapodaster lines"""
        if not kapodaster_lines:
            return ""

        # Sort by Y coordinate and take the first kapodaster
        kapodaster_lines_sorted = sorted(kapodaster_lines, key=lambda x: x['y'])
        kapodaster = kapodaster_lines_sorted[0]['text'].strip()

        print(f"🎸 KAPODASTER (from classification): '{kapodaster}'")
        return kapodaster

    def _extract_comments_from_classified_lines(self, comment_lines: List[Dict]) -> List[str]:
        """Extract comments from classified comment lines - combines multi-line comments"""
        if not comment_lines:
            return []

        # Sort by Y coordinate (top to bottom) to maintain order
        comment_lines_sorted = sorted(comment_lines, key=lambda x: x['y'])

        # Combine multi-line comments
        combined_comments = []
        current_comment = ""

        for line in comment_lines_sorted:
            text = line['text'].strip()

            # Check if this starts a new comment or continues the current one
            if text.startswith('(') and not text.endswith(')'):
                # Start of a multi-line comment
                current_comment = text
            elif text.startswith('bez:') or (text.endswith(')') and current_comment):
                # Continuation or end of multi-line comment
                if current_comment:
                    current_comment += "\n" + " " * 20 + text  # Add indentation for continuation
                    if text.endswith(')'):
                        # End of multi-line comment
                        combined_comments.append(current_comment)
                        current_comment = ""
                else:
                    # Standalone continuation line (shouldn't happen, but handle it)
                    combined_comments.append(text)
            else:
                # Complete single-line comment or other comment type
                if current_comment:
                    # Finish previous multi-line comment
                    combined_comments.append(current_comment)
                    current_comment = ""
                combined_comments.append(text)

        # Handle case where multi-line comment doesn't end properly
        if current_comment:
            combined_comments.append(current_comment)

        print(f"💬 COMMENTS (from classification): {len(combined_comments)} found")
        for comment in combined_comments:
            print(f"    💬 '{comment}'")

        return combined_comments

    def _parse_verses_with_span_positioning_enhanced(self, text_lines: List[Dict], chord_lines: List[Dict]) -> List[Verse]:
        """Parse verses using span-based chord positioning - enhanced version that only processes verse content"""
        verses = []
        current_verse_lines = []
        current_role = ""

        # Sort text lines by Y coordinate to process in order
        text_lines_sorted = sorted(text_lines, key=lambda x: x['y'])

        # Track processed lines to avoid duplicates
        processed_indices = set()

        i = 0
        while i < len(text_lines_sorted):
            if i in processed_indices:
                i += 1
                continue

            text_line_data = text_lines_sorted[i]
            text = text_line_data['text']

            if not text.strip():
                i += 1
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
                processed_indices.add(i)  # Mark role marker line as processed

                # Check if role marker is on same line as text or separate line
                if len(text.strip()) > len(role_marker.strip()) + 2:
                    # Role marker and text on same line (like 2-02-pok9.pdf)
                    text_after_role = text_line_data['text_content']

                    # Find chords using span-based positioning
                    chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)

                    # Check if this is an inline comment (MUST be pink text in parentheses)
                    is_pink = text_line_data.get('is_pink', False)
                    if (is_pink and
                        text_after_role.strip().startswith('(') and
                        text_after_role.strip().endswith(')')):
                        # Format as inline comment with empty line before
                        formatted_text = f"\n{{comment: {text_after_role.strip()}}}"
                        verse_line = VerseLine(
                            text=formatted_text,
                            chords=[],  # Comments don't have chords
                            original_line=text
                        )
                    else:
                        verse_line = VerseLine(
                            text=text_after_role,
                            chords=chords,
                            original_line=text
                        )
                    current_verse_lines = [verse_line]
                    print(f"🎵 Started verse: {current_role} (same line)")

                else:
                    # Role marker on separate line (like 2-03-blag.pdf)
                    # Look for text content on next line(s)
                    current_verse_lines = []
                    print(f"🎵 Started verse: {current_role} (separate line)")

                    # Continue to next line to find the actual text
                    j = i + 1
                    while j < len(text_lines_sorted):
                        next_line_data = text_lines_sorted[j]
                        next_text = next_line_data['text']

                        if not next_text.strip():
                            j += 1
                            continue

                        # Stop if we hit another role marker
                        if self._extract_role_marker(next_text):
                            break

                        # This is text content for the current role
                        chords = self._find_chords_with_span_positioning(next_line_data, chord_lines)

                        # Check if this is an inline comment (MUST be pink text in parentheses)
                        line_text = next_line_data.get('text_content', next_text.strip())
                        is_pink = next_line_data.get('is_pink', False)
                        if (is_pink and
                            line_text.strip().startswith('(') and
                            line_text.strip().endswith(')')):
                            # Format as inline comment with empty line before
                            formatted_text = f"\n{{comment: {line_text.strip()}}}"
                            verse_line = VerseLine(
                                text=formatted_text,
                                chords=[],  # Comments don't have chords
                                original_line=next_text
                            )
                        else:
                            verse_line = VerseLine(
                                text=line_text,
                                chords=chords,
                                original_line=next_text
                            )
                        current_verse_lines.append(verse_line)
                        processed_indices.add(j)  # Mark this line as processed
                        print(f"    📝 Added text line: '{next_text.strip()[:50]}...'")

                        j += 1

            elif current_role:
                # Continuation line in current verse
                # Handle continuation lines (including those with quotes like in 2-02-pok9.pdf)
                clean_text = text.strip()

                # Remove leading quotes and spaces for continuation lines
                if clean_text.startswith('""'):
                    clean_text = clean_text.replace('""', '').strip()
                    clean_text = clean_text.replace('"', '').strip()

                if clean_text:  # Only add if there's actual content
                    # Find chords using span-based positioning
                    chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)

                    # Check if this is an inline comment (MUST be pink text in parentheses)
                    is_pink = text_line_data.get('is_pink', False)
                    if (is_pink and
                        clean_text.strip().startswith('(') and
                        clean_text.strip().endswith(')')):
                        # Format as inline comment with empty line before
                        formatted_text = f"\n{{comment: {clean_text.strip()}}}"
                        verse_line = VerseLine(
                            text=formatted_text,
                            chords=[],  # Comments don't have chords
                            original_line=text
                        )
                    else:
                        verse_line = VerseLine(
                            text=clean_text,
                            chords=chords,
                            original_line=text
                        )
                    current_verse_lines.append(verse_line)
                    processed_indices.add(i)  # Mark this line as processed
                    print(f"    📝 Added continuation line: '{clean_text[:50]}...'")

            i += 1

        # Add final verse
        if current_verse_lines and current_role:
            verses.append(Verse(role=current_role, lines=current_verse_lines))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines")

        # Handle unprocessed text lines - create default verse for content without roles
        # This handles both: 1) Songs with no roles at all, 2) Mixed songs with some content without roles
        unprocessed_lines = []
        for i, text_line_data in enumerate(text_lines_sorted):
            if i not in processed_indices:
                text = text_line_data['text']
                if text.strip():
                    unprocessed_lines.append(text_line_data)

        if unprocessed_lines:
            if not verses:
                print("🎵 No role markers found - creating default verse for song without roles")
            else:
                print(f"🎵 Found {len(unprocessed_lines)} unprocessed text lines - creating default verse for content without roles")

            default_verse_lines = []

            for text_line_data in unprocessed_lines:
                text = text_line_data['text']

                # Find chords using span-based positioning
                chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)

                # Check if this is an inline comment (MUST be pink text in parentheses)
                is_pink = text_line_data.get('is_pink', False)
                if (is_pink and
                    text.strip().startswith('(') and
                    text.strip().endswith(')')):
                    # Format as inline comment
                    formatted_text = f"{{comment: {text.strip()}}}"
                    verse_line = VerseLine(
                        text=formatted_text,
                        chords=[],  # Comments don't have chords
                        original_line=text
                    )
                else:
                    verse_line = VerseLine(
                        text=text.strip(),
                        chords=chords,
                        original_line=text
                    )
                default_verse_lines.append(verse_line)
                print(f"    📝 Added line to default verse: '{text.strip()[:50]}...'")

            if default_verse_lines:
                # Insert default verse at the beginning (before any role-based verses)
                verses.insert(0, Verse(role="", lines=default_verse_lines))
                print(f"🎭 Created default verse with {len(default_verse_lines)} lines")

        return verses

    def _parse_verses_with_span_positioning(self, text_lines: List[Dict], chord_lines: List[Dict]) -> Tuple[List[Verse], List[str]]:
        """Parse verses using span-based chord positioning - improved to handle all file types"""
        verses = []
        comments = []
        current_verse_lines = []
        current_role = ""

        i = 0
        while i < len(text_lines):
            text_line_data = text_lines[i]
            text = text_line_data['text']

            if not text.strip():
                i += 1
                continue

            # Check for comment
            if self._is_comment_line(text):
                comments.append(text.strip())
                print(f"💬 COMMENT: '{text.strip()}'")
                i += 1
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

                # Check if role marker is on same line as text or separate line
                if len(text.strip()) > len(role_marker.strip()) + 2:
                    # Role marker and text on same line (like 2-02-pok9.pdf)
                    text_after_role = text_line_data['text_content']

                    # Find chords using span-based positioning
                    chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)

                    verse_line = VerseLine(
                        text=text_after_role,
                        chords=chords,
                        original_line=text
                    )
                    current_verse_lines = [verse_line]
                    print(f"🎵 Started verse: {current_role} (same line)")

                else:
                    # Role marker on separate line (like 2-03-blag.pdf)
                    # Look for text content on next line(s)
                    current_verse_lines = []
                    print(f"🎵 Started verse: {current_role} (separate line)")

                    # Continue to next line to find the actual text
                    i += 1
                    while i < len(text_lines):
                        next_line_data = text_lines[i]
                        next_text = next_line_data['text']

                        if not next_text.strip():
                            i += 1
                            continue

                        # Stop if we hit another role marker or chord line
                        if (self._extract_role_marker(next_text) or
                            self._is_chord_line_text(next_text)):
                            i -= 1  # Back up one line
                            break

                        # This is text content for the current role
                        chords = self._find_chords_with_span_positioning(next_line_data, chord_lines)

                        verse_line = VerseLine(
                            text=next_line_data.get('text_content', next_text.strip()),
                            chords=chords,
                            original_line=next_text
                        )
                        current_verse_lines.append(verse_line)
                        print(f"    📝 Added text line: '{next_text.strip()[:50]}...'")

                        i += 1

                    i -= 1  # Adjust for the outer loop increment

            elif current_role:
                # Continuation line in current verse
                if not self._is_chord_line_text(text):
                    # Handle continuation lines (including those with quotes like in 2-02-pok9.pdf)
                    clean_text = text.strip()

                    # Remove leading quotes and spaces for continuation lines
                    if clean_text.startswith('""'):
                        clean_text = clean_text.replace('""', '').strip()
                        clean_text = clean_text.replace('"', '').strip()

                    if clean_text:  # Only add if there's actual content
                        # Find chords using span-based positioning
                        chords = self._find_chords_with_span_positioning(text_line_data, chord_lines)

                        verse_line = VerseLine(
                            text=clean_text,
                            chords=chords,
                            original_line=text
                        )
                        current_verse_lines.append(verse_line)
                        print(f"    📝 Added continuation line: '{clean_text[:50]}...'")

            i += 1

        # Add final verse
        if current_verse_lines and current_role:
            verses.append(Verse(role=current_role, lines=current_verse_lines))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines")

        return verses, comments

    def _find_chords_with_span_positioning(self, text_line_data: Dict, chord_lines: List[Dict]) -> List[ChordPosition]:
        """Find chords using span-based positioning - only if chord line is directly above"""
        chords = []

        text_y = text_line_data['y']

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

        # Check if the chord line is reasonably close (within ~15 pixels)
        # This prevents applying distant chord lines to unrelated text
        distance = text_y - best_chord_line['y']
        if distance > 18.0:  # Increased threshold to catch more chord lines
            print(f"      ⚠️ Chord line too far away (distance: {distance:.1f}px) - skipping chords")
            return chords

        print(f"      🔍 Found chord line above: '{best_chord_line['text'].strip()}' (distance: {distance:.1f}px)")

        # Extract chord positions from the chord span
        chord_positions = self.find_chord_positions_in_span(
            best_chord_line['text'],
            best_chord_line['x_start'],
            best_chord_line['width']
        )

        # Map each chord position to verse character position
        for chord_name, chord_pixel_x in chord_positions:
            char_position = self.map_chord_to_verse_position(
                chord_pixel_x,
                best_chord_line['x_start'],
                best_chord_line['width'],
                text_line_data['text_content'],
                text_line_data['x_start'],
                text_line_data['width'],
                text_line_data['font_size']
            )

            chords.append(ChordPosition(
                chord=chord_name,
                position=char_position,
                x_coord=chord_pixel_x
            ))

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

        # Process verses
        for verse in song.verses:
            for i, line in enumerate(verse.lines):
                if line.chords:
                    chordpro_line = self._position_chords_in_lyrics(line.chords, line.text)
                else:
                    chordpro_line = line.text

                # Add role prefix ONLY on first line of verse (if role exists)
                if i == 0 and verse.role:
                    chordpro_lines.append(f"{verse.role}\t{chordpro_line}")
                elif i == 0:
                    # No role - just add the line without role prefix
                    chordpro_lines.append(chordpro_line)
                else:
                    # Continuation lines - add tab only if there was a role
                    if verse.role:
                        chordpro_lines.append(f"\t{chordpro_line}")
                    else:
                        chordpro_lines.append(chordpro_line)

            chordpro_lines.append("")

        # Add comments at the bottom
        for comment in song.comments:
            chordpro_lines.append(f"{{comment: {comment}}}")

        return '\n'.join(chordpro_lines)

    def _position_chords_in_lyrics(self, chords: List[ChordPosition], lyric_text: str) -> str:
        """Position chords within lyric text using span-based positions"""
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

            # Handle chords at or beyond the end of text
            if chord_pos >= len(lyric_text):
                # Add remaining text first, then chord at the end
                if lyric_pos < len(lyric_text):
                    result += lyric_text[lyric_pos:]
                    lyric_pos = len(lyric_text)
                result += f"[{chord.chord}]"
            else:
                # Normal chord positioning within text
                target_lyric_pos = chord_pos

                if target_lyric_pos > lyric_pos:
                    result += lyric_text[lyric_pos:target_lyric_pos]
                    lyric_pos = target_lyric_pos

                result += f"[{chord.chord}]"

        # Add any remaining text
        if lyric_pos < len(lyric_text):
            result += lyric_text[lyric_pos:]

        return result

def sanitize_filename(title: str) -> str:
    """Sanitize song title for use as filename"""
    if not title:
        return ""

    # Remove or replace problematic characters
    # Keep: letters, numbers, spaces, hyphens, parentheses
    import re

    # Replace problematic characters with safe alternatives
    sanitized = title
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)  # Remove Windows forbidden chars
    sanitized = re.sub(r'[^\w\s\-\(\)\.]+', '', sanitized)  # Keep only word chars, spaces, hyphens, parentheses, dots
    sanitized = re.sub(r'\s+', ' ', sanitized)  # Replace multiple spaces with single space
    sanitized = sanitized.strip()  # Remove leading/trailing spaces

    # Limit length to avoid filesystem issues
    if len(sanitized) > 100:
        sanitized = sanitized[:100].strip()

    return sanitized

def main():
    parser = argparse.ArgumentParser(description='PyMuPDF Span-Based Parser for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, help='PDF file to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    span_parser = PyMuPDFSpanParser()

    # Parse and export
    chordpro_content = span_parser.parse_and_export(args.input, args.song_name or "")

    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        # Generate filename based on song title
        import os
        import re
        input_basename = os.path.splitext(os.path.basename(args.input))[0]

        # Generate consecutive numbering for all songs
        # Check if we have a global counter file
        counter_file = os.path.join(os.path.dirname(args.input), '..', '04_chordpro', '.song_counter')

        # Read or initialize counter
        if os.path.exists(counter_file):
            try:
                with open(counter_file, 'r') as f:
                    counter = int(f.read().strip())
            except:
                counter = 1
        else:
            counter = 1

        # Format counter with leading zeros (001, 002, etc.)
        if counter < 10:
            number_prefix = f"00{counter}-"
        elif counter < 100:
            number_prefix = f"0{counter}-"
        else:
            number_prefix = f"{counter}-"

        # Increment and save counter for next song
        counter += 1
        os.makedirs(os.path.dirname(counter_file), exist_ok=True)
        with open(counter_file, 'w') as f:
            f.write(str(counter))

        # Extract title from ChordPro content
        song_title = ""
        for line in chordpro_content.split('\n'):
            if line.strip().startswith('{title:'):
                song_title = line.strip()[7:-1].strip()  # Remove {title: and }
                break

        # Create filename with title
        if song_title:
            sanitized_title = sanitize_filename(song_title)
            if sanitized_title:
                title_based_filename = f"{number_prefix}{sanitized_title}.chordpro"
                # Determine output directory
                if args.output:
                    # Use directory from --output parameter
                    output_dir = os.path.dirname(args.output)
                    output_file = os.path.join(output_dir, title_based_filename)
                else:
                    # Use same directory as input file
                    output_file = title_based_filename
                print(f"✅ ChordPro exported to: {title_based_filename}")
            else:
                output_file = f"{input_basename}.chordpro"
        else:
            output_file = f"{input_basename}.chordpro"

    # Write output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {output_file}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
