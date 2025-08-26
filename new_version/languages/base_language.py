"""
Base language configuration class.
All language-specific configurations inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Set, Pattern, Optional
import re


class LanguageConfig(ABC):
    """Base configuration class for language-specific settings"""
    
    def __init__(self):
        # Basic language info
        self.language_code: str = ""
        self.language_name: str = ""
        
        # Role markers (order matters - longer ones first)
        self.role_markers: List[str] = []
        
        # Chord system
        self.chord_letters: List[str] = []
        self.chord_numbers: List[str] = []
        self.chord_modifiers: List[str] = []  # sus, dim, aug, etc.
        
        # Character encoding fixes
        self.encoding_fixes: Dict[str, str] = {}
        
        # Comment markers
        self.inline_comment_prefix: str = "C:"
        self.comment_patterns: List[Pattern] = []
        
        # Title recognition patterns
        self.title_patterns: List[Pattern] = []
        
        # Kapodaster patterns
        self.kapodaster_patterns: List[Pattern] = []
        
        # Font size thresholds
        self.title_font_size_min: float = 12.0
        self.text_font_size_min: float = 10.0
        self.chord_font_size_min: float = 10.0
        
        # Initialize after subclass sets basic properties
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize regex patterns after basic properties are set"""
        # Compile comment patterns
        if hasattr(self, 'inline_comment_prefix'):
            self.comment_patterns = [
                re.compile(rf'^{re.escape(self.inline_comment_prefix)}\s*(.+)$'),
            ]
        
        # Compile kapodaster patterns
        self.kapodaster_patterns = [
            re.compile(r'[Kk]apodaster.*', re.IGNORECASE),
            re.compile(r'[Cc]apo.*', re.IGNORECASE),
        ]
    
    @property
    def valid_chords(self) -> Set[str]:
        """Generate all valid chord combinations"""
        chords = set()
        
        # Add base chords (major and minor)
        for chord in self.chord_letters:
            chords.add(chord)  # Major
            chords.add(chord.lower())  # Minor
        
        # Add numbered variations
        for chord in self.chord_letters:
            for num in self.chord_numbers:
                chords.add(f"{chord}{num}")  # Major with number
                chords.add(f"{chord.lower()}{num}")  # Minor with number
        
        # Add modifier variations
        for chord in self.chord_letters:
            for modifier in self.chord_modifiers:
                chords.add(f"{chord}{modifier}")
                chords.add(f"{chord.lower()}{modifier}")
        
        return chords
    
    def is_valid_chord(self, text: str) -> bool:
        """Check if text represents a valid chord"""
        # First check direct match
        if text in self.valid_chords:
            return True
        
        # Check normalized version (for spaced chords like "H 7")
        normalized = self.normalize_chord(text)
        return normalized in self.valid_chords
    
    def normalize_chord(self, chord_text: str) -> str:
        """Normalize chord text (e.g., 'H 7' -> 'H7')"""
        if not chord_text:
            return chord_text
        
        # Remove spaces between chord letter(s) and numbers
        normalized = re.sub(r'([A-H][a-z]*)\s+(\d+)', r'\1\2', chord_text)
        return normalized
    
    def fix_text_encoding(self, text: str) -> str:
        """Apply language-specific encoding fixes"""
        if not text:
            return text
        
        result = text
        for wrong_char, correct_char in self.encoding_fixes.items():
            result = result.replace(wrong_char, correct_char)
        
        return result
    
    def is_role_marker(self, text: str) -> Optional[str]:
        """Check if text contains a role marker, return the marker if found"""
        text = text.strip()
        for role in sorted(self.role_markers, key=len, reverse=True):
            if text.startswith(role):
                return role
        return None
    
    def is_inline_comment(self, text: str) -> bool:
        """Check if text is an inline comment"""
        text = text.strip()
        return text.startswith(self.inline_comment_prefix)
    
    def extract_inline_comment(self, text: str) -> str:
        """Extract comment text from inline comment"""
        text = text.strip()
        if text.startswith(self.inline_comment_prefix):
            return text[len(self.inline_comment_prefix):].strip()
        return text
    
    def is_title_text(self, text: str, font_size: float, is_bold: bool = False) -> bool:
        """Determine if text looks like a title"""
        # Check font size
        if font_size < self.title_font_size_min:
            return False
        
        # Check against title patterns
        for pattern in self.title_patterns:
            if pattern.match(text.strip()):
                return True
        
        return False
    
    def is_kapodaster_text(self, text: str) -> bool:
        """Check if text is kapodaster information"""
        for pattern in self.kapodaster_patterns:
            if pattern.match(text.strip()):
                return True
        return False
    
    def looks_like_chord_line(self, text: str) -> bool:
        """Determine if a line contains primarily chords"""
        words = text.split()
        if not words:
            return False
        
        # Special case: single spaced chord like "H 7"
        if len(words) == 2:
            normalized_chord = self.normalize_chord(' '.join(words))
            if self.is_valid_chord(normalized_chord):
                return True
        
        # Check proportion of valid chords
        chord_count = 0
        for word in words:
            if self.is_valid_chord(word):
                chord_count += 1
        
        return (chord_count / len(words)) > 0.6
    
    @abstractmethod
    def get_custom_processing_rules(self) -> Dict[str, any]:
        """Return language-specific processing rules"""
        pass
    
    def __str__(self) -> str:
        return f"LanguageConfig({self.language_name}, {self.language_code})"
