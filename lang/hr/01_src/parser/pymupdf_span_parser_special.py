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
    y_coordinate: float = 0.0  # Y-coordinate for proper ordering in special songs

@dataclass
class Song:
    title: str
    kapodaster: str
    verses: List[Verse]
    comments: List[str]

class PyMuPDFSpanParser:
    def __init__(self):
        self.role_markers = ['K.+Z.', 'K.', 'Z.', 'P.']
        self.additional_titles = []  # For special songs with multiple titles
        
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
                            # Comment line - pink with parentheses or starts with * or **
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

        # Check if text is mostly uppercase (allowing for mixed case in parentheses)
        # Remove parentheses content for uppercase check
        import re
        text_without_parens = re.sub(r'\([^)]*\)', '', text_clean).strip()
        is_mostly_uppercase = text_without_parens.isupper() if text_without_parens else text_clean.isupper()

        # SPECIAL CASE: Mid-song titles for 2-08-drug-ALL.pdf
        # Handle titles like "nastavlja DRUGA EUHARISTIJSKA MOLITVA (1): Posveta i Poklik"
        if (is_pink and
            font_size >= 12.0 and
            len(text_clean) > 20 and
            ('DRUGA EUHARISTIJSKA MOLITVA' in text_clean or 'nastavlja' in text_clean.lower())):
            return True

        # Title criteria: mostly uppercase, reasonable length, larger font (pink is preferred but not required)
        return (is_mostly_uppercase and
                len(text_clean) > 8 and
                font_size >= 12.0 and  # Larger or equal font (relaxed requirement)
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

        # Type 1: Pink with parentheses
        if (is_pink and
            text_clean.startswith('(') and
            ('slijedi' in text_clean.lower() or 'bez:' in text_clean.lower() or ')' in text_clean)):
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

        # SPECIAL CASE: Mid-song comments for 2-08-drug-ALL.pdf
        # Handle comments like "(nastaviti sa "SVET" liturgijskog vremena)"
        if (is_pink and
            text_clean.startswith('(') and
            ('nastaviti' in text_clean.lower() or 'liturgijskog vremena' in text_clean.lower())):
            return True

        # SPECIAL CASE: Handle continuation of multi-line comments
        # Second part: "liturgijskog vremena)" without pink color
        if (text_clean.endswith(')') and
            'liturgijskog vremena' in text_clean.lower()):
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

        # Sort by Y coordinate (top to bottom)
        title_lines_sorted = sorted(title_lines, key=lambda x: x['y'])

        # SPECIAL CASE: For 2-08-drug-ALL.pdf, store additional titles for inline processing
        if len(title_lines_sorted) > 1:
            # Use the first title as main title
            title = title_lines_sorted[0]['text'].strip()
            print(f"📋 TITLE (from classification): '{title}' (+ {len(title_lines_sorted)-1} additional titles)")

            # Store additional titles with their Y coordinates for inline processing
            self.additional_titles = []
            for i, title_line in enumerate(title_lines_sorted[1:], 1):
                additional_title = title_line['text'].strip()
                self.additional_titles.append({
                    'text': additional_title,
                    'y': title_line['y']
                })
                print(f"📋 Additional title {i}: '{additional_title}' (Y: {title_line['y']})")
        else:
            title = title_lines_sorted[0]['text'].strip()
            print(f"📋 TITLE (from classification): '{title}'")
            self.additional_titles = []

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
                    # Use Y-coordinate of the role marker line (current line)
                    verse_y = text_line_data.get('y', 0.0)
                    verses.append(Verse(role=current_role, lines=current_verse_lines, y_coordinate=verse_y))
                    print(f"🎭 Completed verse: {current_role} with {len(current_verse_lines)} lines (Y: {verse_y})")

                # Start new verse
                current_role = role_marker
                processed_indices.add(i)  # Mark role marker line as processed

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

                        verse_line = VerseLine(
                            text=next_line_data.get('text_content', next_text.strip()),
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
            # Use Y-coordinate of last processed line
            verse_y = text_lines[-1].get('y', 0.0) if text_lines else 0.0
            verses.append(Verse(role=current_role, lines=current_verse_lines, y_coordinate=verse_y))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines (Y: {verse_y})")

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
                    # Use Y-coordinate of the role marker line (current line)
                    verse_y = text_line_data.get('y', 0.0)
                    verses.append(Verse(role=current_role, lines=current_verse_lines, y_coordinate=verse_y))
                    print(f"🎭 Completed verse: {current_role} with {len(current_verse_lines)} lines (Y: {verse_y})")

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
            # Use Y-coordinate of last processed line
            verse_y = text_lines[-1].get('y', 0.0) if text_lines else 0.0
            verses.append(Verse(role=current_role, lines=current_verse_lines, y_coordinate=verse_y))
            print(f"🎭 Completed final verse: {current_role} with {len(current_verse_lines)} lines (Y: {verse_y})")

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
        if distance > 15.0:
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
        """Export song to ChordPro format with special handling for inline content"""
        # Check if this is the special song that needs inline processing
        if 'DRUGA EUHARISTIJSKA MOLITVA' in song.title:
            return self._export_to_chordpro_special_inline(song)
        else:
            return self._export_to_chordpro_standard(song)

    def _export_to_chordpro_standard(self, song: Song) -> str:
        """Standard export - comments at bottom, single title at top"""
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

                # Add role prefix ONLY on first line of verse
                if i == 0:
                    chordpro_lines.append(f"{verse.role}\t{chordpro_line}")
                else:
                    chordpro_lines.append(f"\t{chordpro_line}")

            chordpro_lines.append("")

        # Add comments at the bottom
        for comment in song.comments:
            chordpro_lines.append(f"{{comment: {comment}}}")

        return "\n".join(chordpro_lines)

    def _export_to_chordpro_special_inline(self, song: Song) -> str:
        """Special export for 2-08-drug-ALL.pdf - preserves inline comments and titles"""
        chordpro_lines = []

        # Add main title
        if song.title:
            chordpro_lines.append(f"{{title: {song.title}}}")
            chordpro_lines.append("")

        # Add kapodaster if present
        if song.kapodaster:
            chordpro_lines.append(f"{{comment: {song.kapodaster}}}")
            chordpro_lines.append("")

        print("🎵 Using special inline processing for DRUGA EUHARISTIJSKA MOLITVA")

        # Create a list of all content elements with their Y-coordinates for proper ordering
        content_elements = []

        # Add verses with their Y-coordinates (use first line Y-coordinate of each verse)
        for verse in song.verses:
            if hasattr(verse, 'y_coordinate'):
                content_elements.append({
                    'type': 'verse',
                    'y': verse.y_coordinate,
                    'content': verse
                })
            else:
                # Fallback: add without Y-coordinate (will be processed in original order)
                content_elements.append({
                    'type': 'verse',
                    'y': float('inf'),  # Put at end if no Y-coordinate
                    'content': verse
                })

        # Add additional titles with their Y-coordinates
        if hasattr(self, 'additional_titles') and self.additional_titles:
            for additional_title in self.additional_titles:
                content_elements.append({
                    'type': 'title',
                    'y': additional_title['y'],
                    'content': additional_title['text']
                })

        # Add comments with their Y-coordinates (if available)
        for comment in song.comments:
            content_elements.append({
                'type': 'comment',
                'y': float('inf'),  # For now, put comments at end (will enhance later)
                'content': comment
            })

        # Sort all elements by Y-coordinate
        content_elements.sort(key=lambda x: x['y'])

        # Process elements in Y-coordinate order
        for element in content_elements:
            if element['type'] == 'verse':
                verse = element['content']
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

            elif element['type'] == 'title':
                # Add empty line before second title for proper spacing
                chordpro_lines.append("")
                chordpro_lines.append(f"{{comment: === {element['content']} ===}}")
                chordpro_lines.append("")

            elif element['type'] == 'comment':
                chordpro_lines.append(f"{{comment: {element['content']}}}")

        return "\n".join(chordpro_lines)
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

def main():
    parser = argparse.ArgumentParser(description='PyMuPDF Span-Based Parser for Croatian Songs')
    parser.add_argument('--input', '-i', required=True, help='PDF file to parse')
    parser.add_argument('--output', '-o', help='Output ChordPro file')
    parser.add_argument('--song-name', '-s', help='Song name for display')

    args = parser.parse_args()

    span_parser = PyMuPDFSpanParser()

    # Parse and export
    chordpro_content = span_parser.parse_and_export(args.input, args.song_name or "")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        print(f"✅ ChordPro exported to: {args.output}")
    else:
        print(chordpro_content)

if __name__ == "__main__":
    main()
