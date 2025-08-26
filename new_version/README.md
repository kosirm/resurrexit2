# Universal Songbook Parser Architecture

## 🎯 Overview

This is a modern, language-agnostic parser framework for processing songbook PDFs across multiple languages (Croatian, Slovenian, Italian, etc.). The architecture eliminates code duplication and provides a scalable foundation for adding new languages.

## 🏗️ Architecture

### Core Principles
- **DRY (Don't Repeat Yourself)**: Common logic written once, reused everywhere
- **Configuration-Driven**: Language differences handled via config files
- **Separation of Concerns**: Each component has a single responsibility
- **Extensibility**: New languages require minimal code
- **Maintainability**: Bug fixes benefit all languages

### Directory Structure
```
git2/new_version/
├── core/                    # Language-agnostic core functionality
│   ├── base_parser.py      # Abstract base parser
│   ├── pdf_extractor.py    # PDF text/chord extraction
│   ├── chord_detector.py   # Universal chord detection
│   ├── text_classifier.py  # Text type classification
│   ├── verse_builder.py    # Verse construction logic
│   ├── chordpro_exporter.py # ChordPro format export
│   ├── html_generator.py   # HTML generation
│   └── models.py           # Data models (Song, Verse, etc.)
├── languages/              # Language-specific configurations
│   ├── base_language.py    # Base language configuration
│   ├── croatian/
│   │   ├── config.py       # Croatian settings
│   │   └── customizations.py # Croatian-specific logic
│   ├── slovenian/
│   │   ├── config.py       # Slovenian settings
│   │   └── customizations.py # Slovenian-specific logic
│   └── italian/
│       ├── config.py       # Italian settings
│       └── customizations.py # Italian-specific logic
├── parsers/
│   └── universal_parser.py # Main parser entry point
├── tests/                  # Unit tests
│   ├── test_core/
│   ├── test_languages/
│   └── test_integration/
└── examples/               # Usage examples
    └── parse_song.py
```

## 🚀 Key Features

### 1. Universal Core
- Single PDF extraction engine for all languages
- Common chord detection and positioning logic
- Unified verse building and role assignment
- Consistent ChordPro and HTML export

### 2. Language Configuration
- Role markers (K., Z., P., D./O., etc.)
- Chord systems and notation
- Character encoding fixes
- Comment markers and patterns
- Title recognition patterns

### 3. Extensible Customizations
- Language-specific text processing
- Custom verse building logic
- Special formatting rules
- Inline comment handling

### 4. Modern Development Practices
- Type hints throughout
- Comprehensive unit tests
- Clear separation of concerns
- Abstract base classes
- Configuration-driven design

## 📋 Implementation Status

### ✅ Completed Features (from current parsers)
- PDF text and chord extraction
- Role marker detection and assignment
- Chord positioning and normalization
- ChordPro export format
- HTML generation with chord positioning
- Character encoding fixes (č/Č issues)
- Inline comment handling (C: comments)
- Spaced chord normalization (H 7 → H7)

### 🔄 Migration Tasks
1. Create core framework structure
2. Extract common logic from existing parsers
3. Create language configuration files
4. Implement language-specific customizations
5. Add comprehensive test suite
6. Validate output against existing parsers
7. Update work.sh integration

## 🎵 Language Support

### Croatian (hr)
- Role markers: K.+Z., K.+P., K., Z., P., D. (Djeca)
- Chord system: Standard European notation
- Encoding fixes: è→č, È→Č

### Slovenian (sl)
- Role markers: K.+Z., K.+P., K., Z., P., O. (Otroci)
- Chord system: Standard European notation  
- Encoding fixes: è→č, È→Č

### Italian (it)
- Role markers: TBD
- Chord system: TBD
- Encoding fixes: TBD

## 🔧 Usage Example

```python
from parsers.universal_parser import UniversalParser
from languages.slovenian.config import SlovenianConfig

# Initialize parser with language config
parser = UniversalParser(SlovenianConfig())

# Parse PDF
song = parser.parse("path/to/song.pdf")

# Export formats
chordpro_content = parser.export_chordpro(song)
html_content = parser.export_html(song)

# Save outputs
with open("song.chordpro", "w", encoding="utf-8") as f:
    f.write(chordpro_content)
    
with open("song.html", "w", encoding="utf-8") as f:
    f.write(html_content)
```

## 🧪 Testing Strategy

- **Unit Tests**: Each core component tested independently
- **Integration Tests**: End-to-end parsing validation
- **Language Tests**: Verify language-specific features
- **Regression Tests**: Compare output with existing parsers
- **Performance Tests**: Ensure parsing speed is maintained

## 📈 Benefits

1. **Maintainability**: Single codebase for all languages
2. **Consistency**: Same parsing logic ensures consistent results
3. **Scalability**: Adding new languages is trivial
4. **Quality**: Centralized improvements benefit all languages
5. **Testing**: Comprehensive test coverage for reliability
6. **Documentation**: Clear architecture and usage patterns

## 🔄 Migration Path

1. **Phase 1**: Implement core framework
2. **Phase 2**: Create Slovenian language config
3. **Phase 3**: Validate against existing Slovenian parser
4. **Phase 4**: Create Croatian language config
5. **Phase 5**: Add comprehensive test suite
6. **Phase 6**: Replace existing parsers
7. **Phase 7**: Add Italian and other languages

This architecture provides a solid foundation for scaling to dozens of languages while maintaining code quality and consistency.
