#!/usr/bin/env python3
"""
Script to rename Croatian ChordPro files using Italian song IDs
"""

import os
import re
import shutil
from typing import Dict, List

def load_matches(matches_file: str) -> Dict[str, str]:
    """Load the song matches from the generated markdown file"""
    matches = {}
    
    with open(matches_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the table section
    in_table = False
    for line in lines:
        line = line.strip()
        
        if line.startswith('| ID | Croatian Title'):
            in_table = True
            continue
        elif line.startswith('|----'):
            continue
        elif line.startswith('## Unmatched'):
            break
        elif in_table and line.startswith('|'):
            # Parse table row: | ID | Croatian Title | Biblical Ref | Score |
            parts = [part.strip() for part in line.split('|')[1:-1]]
            if len(parts) >= 2:
                song_id = parts[0].strip()
                croatian_title = parts[1].strip()
                matches[croatian_title] = song_id
    
    return matches

def get_current_files(chordpro_folder: str) -> List[str]:
    """Get list of current ChordPro files"""
    files = []
    if os.path.exists(chordpro_folder):
        for filename in os.listdir(chordpro_folder):
            if filename.endswith('.chordpro'):
                files.append(filename)
    return sorted(files)

def extract_title_from_filename(filename: str) -> str:
    """Extract title from current filename format"""
    # Remove .chordpro extension
    title = filename.replace('.chordpro', '')
    # Remove number prefix like "2-01-" or "3-083-"
    title = re.sub(r'^\d+-\d+-', '', title)
    title = re.sub(r'^\d+-', '', title)
    return title.strip()

def create_new_filename(song_id: str, title: str) -> str:
    """Create new filename with ID prefix"""
    # Clean title for filename (remove problematic characters)
    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
    # Format: ID-TITLE.chordpro
    return f"{song_id.zfill(3)}-{clean_title}.chordpro"

def rename_files(chordpro_folder: str, matches: Dict[str, str], dry_run: bool = True):
    """Rename files based on matches"""
    current_files = get_current_files(chordpro_folder)
    
    renamed_count = 0
    unmatched_count = 0
    
    print(f"📁 Processing {len(current_files)} files in {chordpro_folder}")
    print(f"🔍 {'DRY RUN - ' if dry_run else ''}Renaming files...")
    print("-" * 80)
    
    for filename in current_files:
        title = extract_title_from_filename(filename)
        
        if title in matches:
            song_id = matches[title]
            new_filename = create_new_filename(song_id, title)
            
            old_path = os.path.join(chordpro_folder, filename)
            new_path = os.path.join(chordpro_folder, new_filename)
            
            print(f"✅ {song_id:>3}: {filename}")
            print(f"    → {new_filename}")
            
            if not dry_run:
                try:
                    shutil.move(old_path, new_path)
                    print(f"    ✅ Renamed successfully")
                except Exception as e:
                    print(f"    ❌ Error: {e}")
            
            renamed_count += 1
        else:
            print(f"❓ UNMATCHED: {filename}")
            print(f"    Title: {title}")
            unmatched_count += 1
        
        print()
    
    print("=" * 80)
    print(f"📊 SUMMARY:")
    print(f"   ✅ Matched files: {renamed_count}")
    print(f"   ❓ Unmatched files: {unmatched_count}")
    print(f"   📁 Total files: {len(current_files)}")
    
    if dry_run:
        print(f"\n🔍 This was a DRY RUN. To actually rename files, run with --execute")

def main():
    import sys
    
    print("🎵 Croatian Song File Renamer")
    print("=" * 50)
    
    # Check if we should actually execute or just dry run
    dry_run = '--execute' not in sys.argv
    
    # Load matches
    matches_file = "croatian_song_matches.md"
    if not os.path.exists(matches_file):
        print(f"❌ Matches file not found: {matches_file}")
        print("   Please run match_croatian_songs.py first")
        return
    
    print(f"📖 Loading matches from: {matches_file}")
    matches = load_matches(matches_file)
    print(f"✅ Loaded {len(matches)} song matches")
    
    # Rename files
    chordpro_folder = "lang/hr/04_chordpro"
    rename_files(chordpro_folder, matches, dry_run)

if __name__ == "__main__":
    main()
