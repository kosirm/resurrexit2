#!/usr/bin/env python3
"""
Debug script to investigate title parsing issues in Croatian songs
"""

import sys
import os
sys.path.append('lang/hr/01_src/parser')

from pymupdf_span_parser import PyMuPDFSpanParser
import fitz

def debug_title_parsing(pdf_path):
    """Debug title parsing for a specific PDF file"""
    print(f"🔍 Debugging title parsing for: {pdf_path}")
    print("=" * 60)
    
    # Open PDF
    doc = fitz.open(pdf_path)
    parser = PyMuPDFSpanParser()
    
    # Process first page only for debugging
    page = doc[0]
    text_dict = page.get_text("dict")
    
    print(f"📄 Page dimensions: {page.rect.width} x {page.rect.height}")
    print(f"📄 Number of blocks: {len(text_dict['blocks'])}")
    print()
    
    # Analyze all text lines
    for block_idx, block in enumerate(text_dict['blocks']):
        if 'lines' not in block:
            continue
            
        print(f"📦 Block {block_idx}:")
        for line_idx, line in enumerate(block['lines']):
            if not line['spans']:
                continue
                
            # Get main span (first span)
            main_span = line['spans'][0]
            line_text = ''.join(span['text'] for span in line['spans'])
            
            font_size = main_span.get('size', 0)
            color = main_span.get('color', 0)
            font_name = main_span.get('font', 'Unknown')
            
            # Check if pink
            is_pink = parser._is_pink_color(color)
            
            # Check title criteria
            is_title = parser._is_title_line(line_text, font_size, is_pink)
            
            print(f"  Line {line_idx}: '{line_text.strip()}'")
            print(f"    Font: {font_name}, Size: {font_size:.1f}, Color: {color}, Pink: {is_pink}")
            print(f"    Is Title: {is_title}")
            
            # Additional title analysis
            text_clean = line_text.strip()
            if text_clean:
                import re
                text_without_parens = re.sub(r'\([^)]*\)', '', text_clean).strip()
                is_mostly_uppercase = text_without_parens.isupper() if text_without_parens else text_clean.isupper()
                has_role_markers = any(role in text_clean for role in parser.role_markers)
                is_chord_line = parser._is_chord_line_text(text_clean)
                has_kapodaster = 'kapodaster' in text_clean.lower()
                
                print(f"    Analysis:")
                print(f"      - Uppercase: {is_mostly_uppercase}")
                print(f"      - Length: {len(text_clean)} (>8: {len(text_clean) > 8})")
                print(f"      - Font size: {font_size:.1f} (>=12: {font_size >= 12.0})")
                print(f"      - Has role markers: {has_role_markers}")
                print(f"      - Is chord line: {is_chord_line}")
                print(f"      - Has kapodaster: {has_kapodaster}")
            print()
    
    doc.close()

if __name__ == "__main__":
    # Test with the file provided as argument or default
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "lang/hr/03_pdf/3-100-teb.pdf"

    if os.path.exists(pdf_path):
        debug_title_parsing(pdf_path)
    else:
        print(f"❌ File not found: {pdf_path}")
        print("Available files:")
        if os.path.exists("lang/hr/03_pdf"):
            for f in sorted(os.listdir("lang/hr/03_pdf"))[:10]:
                if f.endswith('.pdf'):
                    print(f"  - {f}")
