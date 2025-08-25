#!/usr/bin/env python3
"""
ChordPro to HTML Converter - Arial Font Version
Uses Arial font (as in original PDF) with precise pixel positioning for chords.
"""

import argparse
import re
from pathlib import Path
from typing import List, Tuple

class ChordProToHTMLArial:
    def __init__(self):
        self.pink_color = "#ec008c"  # Exact pink from PDF
        # Arial character width mapping (approximate, for 14px font)
        self.arial_char_widths = {
            ' ': 4.0,   # Space
            'a': 7.0, 'b': 7.0, 'c': 6.5, 'd': 7.0, 'e': 6.5, 'f': 4.0, 'g': 7.0, 'h': 7.0,
            'i': 3.0, 'j': 3.0, 'k': 6.5, 'l': 3.0, 'm': 10.0, 'n': 7.0, 'o': 7.0, 'p': 7.0,
            'q': 7.0, 'r': 4.5, 's': 6.5, 't': 4.0, 'u': 7.0, 'v': 6.5, 'w': 9.0, 'x': 6.5,
            'y': 6.5, 'z': 6.5,
            'A': 8.5, 'B': 8.0, 'C': 8.5, 'D': 8.5, 'E': 7.5, 'F': 7.0, 'G': 9.0, 'H': 8.5,
            'I': 3.5, 'J': 5.5, 'K': 8.0, 'L': 6.5, 'M': 10.0, 'N': 8.5, 'O': 9.5, 'P': 7.5,
            'Q': 9.5, 'R': 8.0, 'S': 8.0, 'T': 7.5, 'U': 8.5, 'V': 8.5, 'W': 12.0, 'X': 8.5,
            'Y': 8.5, 'Z': 7.5,
            '.': 3.5, ',': 3.5, ':': 3.5, ';': 3.5, '!': 3.5, '?': 6.5, '"': 4.5, "'": 2.5,
            '(': 4.0, ')': 4.0, '[': 3.5, ']': 3.5, '{': 4.5, '}': 4.5, '-': 4.0, '_': 7.0,
            '0': 7.0, '1': 7.0, '2': 7.0, '3': 7.0, '4': 7.0, '5': 7.0, '6': 7.0, '7': 7.0,
            '8': 7.0, '9': 7.0
        }
        self.default_char_width = 7.0  # Default for unknown characters
    
    def calculate_text_width(self, text: str) -> float:
        """Calculate the pixel width of text in Arial font"""
        total_width = 0.0
        for char in text:
            total_width += self.arial_char_widths.get(char, self.default_char_width)
        return total_width
    
    def convert_chordpro_to_html(self, chordpro_content: str) -> str:
        """Convert ChordPro content to HTML with Arial font and precise positioning"""
        lines = chordpro_content.split('\n')
        
        # Extract metadata
        title = self._extract_title(lines)
        kapodaster, comments = self._extract_comments_and_kapodaster(lines)

        # Process content lines
        html_lines = []
        html_lines.append(self._generate_html_header(title))

        # Add title
        if title:
            html_lines.append(f'        <div class="title">{self._escape_html(title)}</div>')

        # Add Kapodaster if present
        if kapodaster:
            html_lines.append(f'        <div class="kapodaster">{self._escape_html(kapodaster)}</div>')
        
        # Process verses
        html_lines.append('        <div class="song-content">')
        
        for line in lines:
            # Skip empty lines and metadata
            if not line.strip() or line.strip().startswith('{'):
                continue
            
            # Process verse line (including continuation lines that start with just tab)
            if '\t' in line:
                # Lines with tabs (role-based format)
                role_part, lyric_part = line.split('\t', 1)
                role = role_part.strip()  # Will be empty for continuation lines

                # Convert ChordPro line to HTML with precise Arial positioning
                chord_html, lyric_html = self._convert_chordpro_line_arial(lyric_part)

                html_lines.append('            <div class="verse-line">')
                html_lines.append(f'                <div class="role-column">{role}</div>')
                html_lines.append('                <div class="lyric-column">')

                if chord_html.strip():  # Only add chord line if there are chords
                    html_lines.append(f'                    <div class="chord-line">{chord_html}</div>')

                html_lines.append(f'                    <div class="lyric-text">{lyric_html}</div>')
                html_lines.append('                </div>')
                html_lines.append('            </div>')
            else:
                # Lines without tabs (songs without roles)
                lyric_part = line.strip()

                # Convert ChordPro line to HTML with precise Arial positioning
                chord_html, lyric_html = self._convert_chordpro_line_arial(lyric_part)

                html_lines.append('            <div class="verse-line">')
                html_lines.append('                <div class="role-column"></div>')  # Empty role column
                html_lines.append('                <div class="lyric-column">')

                if chord_html.strip():  # Only add chord line if there are chords
                    html_lines.append(f'                    <div class="chord-line">{chord_html}</div>')

                html_lines.append(f'                    <div class="lyric-text">{lyric_html}</div>')
                html_lines.append('                </div>')
                html_lines.append('            </div>')
        
        html_lines.append('        </div>')
        
        # Add comments
        if comments:
            html_lines.append('        <div class="comments">')
            for comment in comments:
                html_lines.append(f'            <div class="comment">{self._escape_html(comment)}</div>')
            html_lines.append('        </div>')
        
        html_lines.append('    </div>')
        html_lines.append('</body>')
        html_lines.append('</html>')
        
        return '\n'.join(html_lines)
    
    def _convert_chordpro_line_arial(self, chordpro_line: str) -> Tuple[str, str]:
        """Convert a ChordPro line to chord HTML and lyric HTML with Arial positioning"""
        if '[' not in chordpro_line:
            return "", self._escape_html(chordpro_line)
        
        # Find all chords and their positions
        chord_positions = []
        lyric_text = ""
        pos = 0
        
        # Parse ChordPro format: text[chord]text[chord]...
        parts = re.split(r'(\[[^\]]+\])', chordpro_line)
        
        for part in parts:
            if part.startswith('[') and part.endswith(']'):
                # This is a chord
                chord = part[1:-1]  # Remove brackets
                chord_positions.append((pos, chord))
            else:
                # This is text
                lyric_text += part
                pos += len(part)
        
        # Generate chord HTML with precise Arial positioning
        chord_html = ""
        if chord_positions:
            chord_spans = []
            position_offsets = {}  # Track cumulative offset for each text position

            for i, (pos, chord) in enumerate(chord_positions):
                # Calculate pixel position based on text up to this point
                text_before = lyric_text[:pos]
                base_pixel_pos = self.calculate_text_width(text_before)

                # Handle consecutive chords at the same position
                if pos in position_offsets:
                    # Add cumulative offset for chords at the same position
                    pixel_pos = base_pixel_pos + position_offsets[pos]
                    # Update offset for next chord at this position
                    chord_width = self.calculate_text_width(chord)
                    position_offsets[pos] += chord_width + 5  # 5px spacing between consecutive chords
                else:
                    # First chord at this position
                    pixel_pos = base_pixel_pos
                    chord_width = self.calculate_text_width(chord)
                    position_offsets[pos] = chord_width + 5  # Prepare offset for next chord

                chord_spans.append(f'<span class="chord" style="left: {pixel_pos}px;">{chord}</span>')

            chord_html = ''.join(chord_spans)
        
        return chord_html, self._escape_html(lyric_text)
    
    def _extract_title(self, lines: List[str]) -> str:
        """Extract title from ChordPro metadata"""
        for line in lines:
            if line.strip().startswith('{title:'):
                return line.strip()[7:-1].strip()  # Remove {title: and }
        return ""
    
    def _extract_comments_and_kapodaster(self, lines: List[str]) -> Tuple[str, List[str]]:
        """Extract Kapodaster and comments from ChordPro metadata"""
        kapodaster = ""
        comments = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('{comment:'):
                # Extract the comment content
                comment_content = line[9:]  # Remove '{comment:'

                # Check if it's a Kapodaster line
                if 'kapodaster' in comment_content.lower() or 'kapo' in comment_content.lower():
                    # This is Kapodaster
                    kapodaster = comment_content.rstrip('}').strip()
                else:
                    # This is a regular comment - might be multi-line
                    if comment_content.endswith('}'):
                        # Single line comment
                        comments.append(comment_content.rstrip('}').strip())
                    else:
                        # Multi-line comment - collect until we find the closing }
                        full_comment = comment_content
                        i += 1
                        while i < len(lines) and not lines[i].strip().endswith('}'):
                            full_comment += '\n' + lines[i].strip()
                            i += 1

                        # Add the final line with closing }
                        if i < len(lines):
                            final_line = lines[i].strip()
                            if final_line.endswith('}'):
                                full_comment += '\n' + final_line.rstrip('}').strip()

                        comments.append(full_comment.strip())

            i += 1

        return kapodaster, comments
    
    def _generate_html_header(self, title: str) -> str:
        """Generate HTML header with CSS for Arial font"""
        return f"""<!DOCTYPE html>
<html lang="hr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title or "Croatian Song"}</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;  /* Use Arial as in original PDF */
            font-size: 14px;  /* Match PDF font size */
            line-height: 1.4;
            margin: 20px;
            background-color: #fff;
            color: #231f20;  /* Exact color from PDF */
        }}
        .song-container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        .title {{
            color: {self.pink_color};
            font-weight: bold;
            font-size: 18px;
            text-align: center;
            margin-bottom: 25px;
            text-transform: uppercase;
        }}
        .kapodaster {{
            text-align: center;
            font-style: italic;
            margin-bottom: 20px;
            color: {self.pink_color};  /* Pink like title and chords */
            font-size: 12px;
        }}
        .song-content {{
            display: table;
            width: 100%;
        }}
        .verse-line {{
            display: table-row;
        }}
        .role-column {{
            display: table-cell;
            width: 40px;
            vertical-align: bottom;  /* Align with the lyric text */
            font-weight: bold;
            padding-right: 4px;
            color: #333;
            font-size: 14px;
        }}
        .lyric-column {{
            display: table-cell;
            vertical-align: top;
            position: relative;
        }}
        .chord-line {{
            color: {self.pink_color};
            font-weight: bold;
            font-size: 12px;
            font-family: 'Arial', sans-serif;
            position: relative;
            height: 16px;
            margin-bottom: 2px;
        }}
        .chord {{
            position: absolute;
            top: 0;
            white-space: nowrap;
        }}
        .lyric-text {{
            font-family: 'Arial', sans-serif;  /* Arial font as in PDF */
            font-size: 14px;
            color: #231f20;  /* Exact color from PDF */
        }}
        .comments {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ccc;
        }}
        .comment {{
            color: {self.pink_color};
            font-style: italic;
            margin-bottom: 8px;
            font-size: 12px;
            white-space: pre-line;
        }}
    </style>
</head>
<body>
    <div class="song-container">"""
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))

def main():
    parser = argparse.ArgumentParser(description='Convert ChordPro to HTML with Arial font')
    parser.add_argument('--input', '-i', required=True, help='Input ChordPro file')
    parser.add_argument('--output', '-o', required=True, help='Output HTML file')
    
    args = parser.parse_args()
    
    # Read ChordPro file
    with open(args.input, 'r', encoding='utf-8') as f:
        chordpro_content = f.read()
    
    # Convert to HTML
    converter = ChordProToHTMLArial()
    html_content = converter.convert_chordpro_to_html(chordpro_content)
    
    # Save HTML file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ ChordPro to HTML (Arial) Conversion Complete:")
    print(f"   📄 Input: {args.input}")
    print(f"   🌐 Output: {output_path}")
    print(f"   📊 Size: {len(html_content)} characters")
    print(f"   🎨 Arial font with precise pixel positioning!")

if __name__ == "__main__":
    main()
