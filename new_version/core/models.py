"""
Data models for the universal songbook parser.
These models represent the core data structures used across all languages.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class TextType(Enum):
    """Classification of text elements in the PDF"""
    TITLE = "title"
    ROLE_MARKER = "role_marker"
    VERSE_TEXT = "verse_text"
    CHORD_LINE = "chord_line"
    COMMENT = "comment"
    INLINE_COMMENT = "inline_comment"
    KAPODASTER = "kapodaster"
    UNKNOWN = "unknown"


@dataclass
class Chord:
    """Represents a chord with its position in the text"""
    chord: str          # The chord symbol (e.g., "H7", "a", "C")
    position: int       # Character position in the text line
    pixel_x: float      # X coordinate in the PDF (for positioning)
    
    def __str__(self) -> str:
        return f"[{self.chord}]"


@dataclass
class VerseLine:
    """Represents a single line within a verse"""
    text: str                    # The lyric text
    chords: List[Chord]         # Chords positioned on this line
    original_line: str          # Original text from PDF (for debugging)
    line_type: TextType = TextType.VERSE_TEXT
    
    def to_chordpro(self) -> str:
        """Convert line to ChordPro format with positioned chords"""
        if not self.chords:
            return self.text
            
        # Sort chords by position
        sorted_chords = sorted(self.chords, key=lambda c: c.position)
        
        result = ""
        lyric_pos = 0
        
        for chord in sorted_chords:
            chord_pos = chord.position
            
            # Handle chords at or beyond the end of text
            if chord_pos >= len(self.text):
                # Add remaining text first, then chord at the end
                if lyric_pos < len(self.text):
                    result += self.text[lyric_pos:]
                    lyric_pos = len(self.text)
                result += f"[{chord.chord}]"
            else:
                # Normal chord positioning within text
                target_lyric_pos = chord_pos
                
                # Add text up to chord position
                if target_lyric_pos > lyric_pos:
                    result += self.text[lyric_pos:target_lyric_pos]
                    lyric_pos = target_lyric_pos
                
                # Add chord
                result += f"[{chord.chord}]"
        
        # Add any remaining text
        if lyric_pos < len(self.text):
            result += self.text[lyric_pos:]
            
        return result


@dataclass
class Verse:
    """Represents a verse with role and lines"""
    role: str                   # Role marker (K., Z., P., etc.)
    lines: List[VerseLine]      # Lines in this verse
    verse_type: str = "verse"   # Type: verse, comment, etc.
    
    def to_chordpro(self, use_tabs: bool = True) -> str:
        """Convert verse to ChordPro format"""
        if not self.lines:
            return ""
            
        chordpro_lines = []
        
        for i, line in enumerate(self.lines):
            chordpro_line = line.to_chordpro()
            
            if i == 0 and self.role:
                # First line with role
                if use_tabs:
                    chordpro_lines.append(f"{self.role}\t{chordpro_line}")
                else:
                    chordpro_lines.append(f"{self.role} {chordpro_line}")
            else:
                # Continuation lines
                if self.role and use_tabs:
                    chordpro_lines.append(f"\t{chordpro_line}")
                else:
                    chordpro_lines.append(chordpro_line)
        
        return "\n".join(chordpro_lines)


@dataclass
class Comment:
    """Represents a comment in the song"""
    text: str
    comment_type: str = "general"  # general, inline, kapodaster
    
    def to_chordpro(self) -> str:
        """Convert comment to ChordPro format"""
        if self.comment_type == "inline":
            return f"\n{{comment: {self.text}}}\n"
        else:
            return self.text


@dataclass
class Song:
    """Represents a complete song"""
    title: str
    verses: List[Verse]
    comments: List[Comment]
    kapodaster: Optional[str] = None
    language: str = ""
    source_file: str = ""
    
    def to_chordpro(self) -> str:
        """Convert entire song to ChordPro format"""
        lines = []
        
        # Title
        lines.append(f"{{title: {self.title}}}")
        lines.append("")
        
        # Kapodaster (if present)
        if self.kapodaster:
            lines.append(self.kapodaster)
            lines.append("")
        
        # Verses and comments
        for verse in self.verses:
            if verse.verse_type == "comment":
                # Handle inline comments
                for line in verse.lines:
                    if line.text.startswith("\n{comment:"):
                        lines.append(line.text)
                    else:
                        lines.append(f"{{comment: {line.text}}}")
            else:
                # Regular verse
                verse_content = verse.to_chordpro()
                if verse_content.strip():
                    lines.append(verse_content)
                    lines.append("")
        
        # General comments at the end
        for comment in self.comments:
            if comment.comment_type == "general":
                lines.append(comment.to_chordpro())
        
        return "\n".join(lines)


@dataclass
class PDFTextElement:
    """Raw text element extracted from PDF"""
    text: str
    x: float
    y: float
    width: float
    height: float
    font_size: float
    font_family: str = ""
    is_bold: bool = False
    is_pink: bool = False
    page_number: int = 1
    
    def __str__(self) -> str:
        return f"PDFTextElement('{self.text[:50]}...', x={self.x}, y={self.y})"


@dataclass
class ClassifiedText:
    """Text element with classification"""
    element: PDFTextElement
    text_type: TextType
    confidence: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ParsedDocument:
    """Complete parsed document structure"""
    title: str
    text_elements: List[ClassifiedText]
    chord_elements: List[ClassifiedText]
    comments: List[str]
    kapodaster: Optional[str] = None
    language: str = ""
    source_file: str = ""
