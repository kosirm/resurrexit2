#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import fitz
import sys

def test_pdf_encoding(pdf_path):
    print(f"Testing PDF: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        blocks = page.get_text('dict')['blocks']
        
        for block in blocks:
            if 'lines' in block:
                for line in block['lines']:
                    for span in line['spans']:
                        text = span['text'].strip()
                        if 'Postni' in text or 'čas' in text or 'èas' in text or 'cas' in text or 'SVET' in text:
                            print(f'Found text: "{text}"')
                            print(f'Text bytes: {text.encode("utf-8")}')
                            print(f'Text repr: {repr(text)}')
                            print('---')
        doc.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test the problematic PDF
    test_pdf_encoding("../../../../lang/sl/03_pdf/Pesmarica - 0017.pdf")
