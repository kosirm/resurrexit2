"""
Universal parser that can handle any language by using language-specific configurations.
This is the main entry point for parsing songbook PDFs.
"""

import os
import argparse
from typing import Optional, Type
import logging

from core.base_parser import BaseParser
from core.models import Song, Verse
from languages.base_language import LanguageConfig
from languages.slovenian.config import SlovenianConfig
from languages.croatian.config import CroatianConfig


class UniversalParser(BaseParser):
    """
    Universal parser that can handle any language.
    Uses language-specific configurations and customizations.
    """
    
    def __init__(self, language_config: LanguageConfig):
        super().__init__(language_config)
        
        # Import language-specific customizations
        self.customizations = self._load_customizations()
    
    def _load_customizations(self):
        """Load language-specific customization module"""
        try:
            if self.config.language_code == "sl":
                from languages.slovenian.customizations import SlovenianCustomizations
                return SlovenianCustomizations(self.config)
            elif self.config.language_code == "hr":
                from languages.croatian.customizations import CroatianCustomizations
                return CroatianCustomizations(self.config)
            else:
                # Default to no customizations
                return None
        except ImportError:
            self.logger.warning(f"No customizations found for {self.config.language_code}")
            return None
    
    def apply_customizations(self, verses: list[Verse], document) -> list[Verse]:
        """Apply language-specific customizations"""
        if self.customizations:
            return self.customizations.apply_customizations(verses, document)
        else:
            # No customizations available, return verses as-is
            return verses
    
    @classmethod
    def create_slovenian_parser(cls) -> 'UniversalParser':
        """Create a parser configured for Slovenian"""
        return cls(SlovenianConfig())
    
    @classmethod
    def create_croatian_parser(cls) -> 'UniversalParser':
        """Create a parser configured for Croatian"""
        return cls(CroatianConfig())
    
    @classmethod
    def create_parser_for_language(cls, language_code: str) -> 'UniversalParser':
        """Create a parser for the specified language code"""
        language_configs = {
            'sl': SlovenianConfig,
            'hr': CroatianConfig,
            # Add more languages here as they're implemented
        }
        
        if language_code not in language_configs:
            raise ValueError(f"Unsupported language code: {language_code}")
        
        config_class = language_configs[language_code]
        return cls(config_class())


def main():
    """Command-line interface for the universal parser"""
    parser = argparse.ArgumentParser(description="Universal Songbook PDF Parser")
    
    parser.add_argument("--input", "-i", required=True, 
                       help="Input PDF file path")
    parser.add_argument("--output", "-o", 
                       help="Output file path (without extension)")
    parser.add_argument("--language", "-l", default="sl", 
                       choices=["sl", "hr"], 
                       help="Language code (sl=Slovenian, hr=Croatian)")
    parser.add_argument("--format", "-f", default="chordpro", 
                       choices=["chordpro", "html", "both"], 
                       help="Output format")
    parser.add_argument("--song-name", "-s", 
                       help="Override song name")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create parser for specified language
        universal_parser = UniversalParser.create_parser_for_language(args.language)
        
        # Parse the PDF
        song = universal_parser.parse(args.input, args.song_name)
        
        # Validate the parsed song
        issues = universal_parser.validate_song(song)
        if issues:
            print("⚠️  Validation issues found:")
            for issue in issues:
                print(f"   - {issue}")
        
        # Determine output path
        if args.output:
            output_base = args.output
        else:
            # Generate output path from input filename and song title
            input_dir = os.path.dirname(args.input)
            safe_title = "".join(c for c in song.title if c.isalnum() or c in (' ', '-', '_')).strip()
            output_base = os.path.join(input_dir, safe_title)
        
        # Export in requested format(s)
        if args.format in ["chordpro", "both"]:
            chordpro_path = f"{output_base}.chordpro"
            universal_parser.save_chordpro(song, chordpro_path)
            print(f"✅ ChordPro saved to: {chordpro_path}")
        
        if args.format in ["html", "both"]:
            html_path = f"{output_base}.html"
            universal_parser.save_html(song, html_path)
            print(f"✅ HTML saved to: {html_path}")
        
        # Print processing stats
        stats = universal_parser.get_processing_stats()
        print(f"\n📊 Processing Stats:")
        print(f"   Language: {stats['language']}")
        print(f"   Verses: {len(song.verses)}")
        print(f"   Comments: {len(song.comments)}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
