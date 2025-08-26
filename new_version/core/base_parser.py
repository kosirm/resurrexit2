"""
Base parser class that defines the universal parsing pipeline.
All language-specific parsers inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging

from core.models import Song, Verse, VerseLine, Comment, PDFTextElement, ClassifiedText, ParsedDocument
from core.pdf_extractor import PDFExtractor
from core.chord_detector import ChordDetector
from core.text_classifier import TextClassifier
from core.verse_builder import VerseBuilder
from core.chordpro_exporter import ChordProExporter
from core.html_generator import HTMLGenerator
from languages.base_language import LanguageConfig


class BaseParser(ABC):
    """
    Abstract base parser that defines the universal parsing pipeline.
    Language-specific parsers inherit from this and implement customizations.
    """
    
    def __init__(self, language_config: LanguageConfig):
        self.config = language_config
        self.logger = logging.getLogger(f"{__name__}.{language_config.language_code}")
        
        # Initialize core components
        self.pdf_extractor = PDFExtractor()
        self.chord_detector = ChordDetector(language_config)
        self.text_classifier = TextClassifier(language_config)
        self.verse_builder = VerseBuilder(language_config)
        self.chordpro_exporter = ChordProExporter(language_config)
        self.html_generator = HTMLGenerator(language_config)
        
        self.logger.info(f"Initialized {language_config.language_name} parser")
    
    def parse(self, pdf_path: str, song_name: Optional[str] = None) -> Song:
        """
        Main parsing pipeline - same for all languages.
        
        Args:
            pdf_path: Path to the PDF file to parse
            song_name: Optional song name override
            
        Returns:
            Parsed Song object
        """
        self.logger.info(f"Parsing PDF: {pdf_path}")
        
        try:
            # 1. Extract raw data from PDF
            self.logger.debug("Step 1: Extracting raw data from PDF")
            raw_elements = self.pdf_extractor.extract(pdf_path)
            
            # 2. Apply language-specific text fixes
            self.logger.debug("Step 2: Applying text encoding fixes")
            cleaned_elements = self.apply_text_fixes(raw_elements)
            
            # 3. Classify text elements
            self.logger.debug("Step 3: Classifying text elements")
            classified_document = self.text_classifier.classify(cleaned_elements)
            
            # 4. Detect and position chords
            self.logger.debug("Step 4: Detecting and positioning chords")
            chord_positioned_document = self.chord_detector.detect_and_position(classified_document)
            
            # 5. Build verses with language-specific logic
            self.logger.debug("Step 5: Building verses")
            verses = self.verse_builder.build_verses(chord_positioned_document)
            
            # 6. Apply language-specific customizations
            self.logger.debug("Step 6: Applying language customizations")
            customized_verses = self.apply_customizations(verses, chord_positioned_document)
            
            # 7. Create song object
            self.logger.debug("Step 7: Creating song object")
            song = Song(
                title=song_name or classified_document.title,
                verses=customized_verses,
                comments=[Comment(text=comment) for comment in classified_document.comments],
                kapodaster=classified_document.kapodaster,
                language=self.config.language_code,
                source_file=pdf_path
            )
            
            self.logger.info(f"Successfully parsed song: {song.title}")
            return song
            
        except Exception as e:
            self.logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise
    
    def apply_text_fixes(self, elements: List[PDFTextElement]) -> List[PDFTextElement]:
        """Apply language-specific text encoding fixes"""
        self.logger.debug(f"Applying {len(self.config.encoding_fixes)} encoding fixes")
        
        fixed_elements = []
        for element in elements:
            fixed_text = self.config.fix_text_encoding(element.text)
            
            # Create new element with fixed text
            fixed_element = PDFTextElement(
                text=fixed_text,
                x=element.x,
                y=element.y,
                width=element.width,
                height=element.height,
                font_size=element.font_size,
                font_family=element.font_family,
                is_bold=element.is_bold,
                is_pink=element.is_pink,
                page_number=element.page_number
            )
            fixed_elements.append(fixed_element)
        
        return fixed_elements
    
    @abstractmethod
    def apply_customizations(self, verses: List[Verse], document: ParsedDocument) -> List[Verse]:
        """
        Apply language-specific customizations to verses.
        This method must be implemented by each language-specific parser.
        
        Args:
            verses: List of verses built by the universal verse builder
            document: The parsed document with all classified elements
            
        Returns:
            List of customized verses
        """
        pass
    
    def export_chordpro(self, song: Song) -> str:
        """Export song to ChordPro format"""
        return self.chordpro_exporter.export(song)
    
    def export_html(self, song: Song) -> str:
        """Export song to HTML format"""
        return self.html_generator.generate(song)
    
    def save_chordpro(self, song: Song, output_path: str) -> None:
        """Save song as ChordPro file"""
        chordpro_content = self.export_chordpro(song)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(chordpro_content)
        self.logger.info(f"Saved ChordPro to: {output_path}")
    
    def save_html(self, song: Song, output_path: str) -> None:
        """Save song as HTML file"""
        html_content = self.export_html(song)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info(f"Saved HTML to: {output_path}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about the last parsing operation"""
        return {
            'language': self.config.language_name,
            'language_code': self.config.language_code,
            'valid_chords_count': len(self.config.valid_chords),
            'role_markers': self.config.role_markers,
            'encoding_fixes_applied': len(self.config.encoding_fixes),
        }
    
    def validate_song(self, song: Song) -> List[str]:
        """
        Validate parsed song and return list of warnings/issues.
        
        Returns:
            List of validation messages
        """
        issues = []
        
        # Check if song has title
        if not song.title or not song.title.strip():
            issues.append("Song has no title")
        
        # Check if song has verses
        if not song.verses:
            issues.append("Song has no verses")
        
        # Check for verses without roles
        verses_without_roles = [i for i, v in enumerate(song.verses) if not v.role]
        if verses_without_roles:
            issues.append(f"Verses without roles: {verses_without_roles}")
        
        # Check for empty verses
        empty_verses = [i for i, v in enumerate(song.verses) if not v.lines]
        if empty_verses:
            issues.append(f"Empty verses: {empty_verses}")
        
        # Check for lines without text
        for i, verse in enumerate(song.verses):
            empty_lines = [j for j, line in enumerate(verse.lines) if not line.text.strip()]
            if empty_lines:
                issues.append(f"Verse {i} has empty lines: {empty_lines}")
        
        return issues
    
    def __str__(self) -> str:
        return f"BaseParser({self.config.language_name})"
