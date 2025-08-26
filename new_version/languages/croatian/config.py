"""
Croatian language configuration for the universal parser.
"""

import re
from typing import Dict, List, Pattern
from languages.base_language import LanguageConfig


class CroatianConfig(LanguageConfig):
    """Configuration for Croatian songbook parsing"""
    
    def __init__(self):
        # Set basic properties first
        self.language_code = "hr"
        self.language_name = "Croatian"
        
        # Croatian role markers (D. for Djeca, not O. for Otroci)
        self.role_markers = ['K.+Z.', 'K.+P.', 'K.', 'Z.', 'P.', 'D.']
        
        # Standard European chord notation (same as Slovenian)
        self.chord_letters = [
            'E', 'F', 'FIS', 'G', 'GIS', 'A', 'B', 'H', 'C', 'CIS', 'D', 'DIS',
            'e', 'f', 'fis', 'g', 'gis', 'a', 'b', 'h', 'c', 'cis', 'd', 'dis'
        ]
        
        # Chord numbers and modifiers
        self.chord_numbers = ['7', '9', '11', '13']
        self.chord_modifiers = ['sus', 'dim', 'aug', 'maj', 'min']
        
        # Croatian-specific character encoding fixes
        self.encoding_fixes = {
            'è': 'č',  # Same issue as Slovenian
            'È': 'Č',  # Uppercase version
        }
        
        # Comment markers
        self.inline_comment_prefix = "C:"
        
        # Font size thresholds
        self.title_font_size_min = 12.0
        self.text_font_size_min = 10.0
        self.chord_font_size_min = 10.0
        
        # Initialize patterns after setting properties
        super().__init__()
        
        # Croatian-specific title patterns
        self.title_patterns = [
            re.compile(r'^[A-ZČŠŽĆĐ\s\(\)\-\.\d]+$'),  # Croatian uppercase with special chars
            re.compile(r'^[A-ZČŠŽĆĐ][A-ZČŠŽĆĐ\s\(\)\-\.\d]*$'),  # Must start with uppercase
        ]
        
        # Additional Croatian patterns
        self.kapodaster_patterns.extend([
            re.compile(r'Kapodaster na [IVX]+\. polju', re.IGNORECASE),
        ])
    
    def get_custom_processing_rules(self) -> Dict[str, any]:
        """Croatian-specific processing rules"""
        return {
            'preserve_case_in_roles': True,
            'allow_mixed_case_titles': False,
            'chord_spacing_tolerance': 5.0,  # pixels
            'role_assignment_distance_threshold': 15.0,  # pixels
            'inline_comment_formatting': {
                'add_empty_lines': True,
                'format_as_chordpro_comment': True,
            },
            'verse_continuation_rules': {
                'max_distance_between_lines': 30.0,  # pixels
                'require_role_for_new_verse': False,
            },
            'special_responses': {
                'smiluj_se_shortcut': {
                    'trigger': 'Z. SMILUJ SE...',
                    'expansion': 'Z. SMILUJ SE NAMA, KOJI SMO GREŠNICI, GOSPODINE, SMILUJ SE!'
                }
            }
        }
    
    def is_croatian_specific_text(self, text: str) -> bool:
        """Check for Croatian-specific text patterns"""
        croatian_words = [
            'gospodin', 'bog', 'krist', 'isus', 'marija', 'sveti', 'sveta',
            'amen', 'aleluja', 'halleluja', 'slava', 'hvala', 'grešnici'
        ]
        
        text_lower = text.lower()
        return any(word in text_lower for word in croatian_words)
    
    def get_role_display_name(self, role: str) -> str:
        """Get human-readable role name"""
        role_names = {
            'K.': 'Kantor',
            'Z.': 'Zbor',
            'P.': 'Prezbiter', 
            'D.': 'Djeca',
            'K.+Z.': 'Kantor + Zbor',
            'P.+Z.': 'Prezbiter + Zbor',
        }
        return role_names.get(role, role)
    
    def should_merge_chord_lines(self, line1_y: float, line2_y: float) -> bool:
        """Determine if two chord lines should be merged based on Y position"""
        # Croatian PDFs might have different spacing than Slovenian
        return abs(line1_y - line2_y) < 3.0
    
    def get_chord_positioning_rules(self) -> Dict[str, float]:
        """Croatian-specific chord positioning rules"""
        return {
            'max_chord_distance_from_text': 15.0,  # pixels
            'chord_alignment_tolerance': 2.0,      # pixels
            'prefer_vowel_positioning': True,
            'vowels': 'aeiouAEIOU',
        }
    
    def normalize_title(self, title: str) -> str:
        """Normalize title text for Croatian"""
        # Apply encoding fixes
        title = self.fix_text_encoding(title)
        
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        # Ensure proper capitalization for Croatian titles
        return title.strip()
    
    def process_special_responses(self, text: str) -> str:
        """Handle Croatian-specific response shortcuts"""
        rules = self.get_custom_processing_rules()
        special_responses = rules.get('special_responses', {})
        
        for response_name, response_config in special_responses.items():
            trigger = response_config.get('trigger', '')
            expansion = response_config.get('expansion', '')
            
            if trigger and expansion and trigger in text:
                text = text.replace(trigger, expansion)
        
        return text
    
    def get_export_settings(self) -> Dict[str, any]:
        """Settings for exporting Croatian songs"""
        return {
            'use_tabs_for_alignment': True,
            'preserve_original_spacing': False,
            'add_language_metadata': True,
            'chord_bracket_style': 'square',  # [chord] vs (chord)
            'comment_style': 'chordpro',      # {comment: text}
        }
