#!/usr/bin/env python3

import json
import os
from pathlib import Path

def convert_json_to_markdown():
    """Convert JSON chunks to markdown format for translation workflow"""
    
    # Set up paths
    json_dir = Path("books_to_translate/chunks_20k_per_chunks")
    output_dir = Path("data/chunks_20k")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process all JSON files
    json_files = sorted(json_dir.glob("chunk_*.json"))
    
    for json_file in json_files:
        try:
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract content
            chunk_id = data.get('chunk_id', json_file.stem)
            content = data.get('source_text', '')
            
            # Create markdown filename
            md_filename = output_dir / f"{chunk_id}.md"
            
            # Write markdown file
            with open(md_filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Converted: {json_file.name} -> {md_filename.name}")
            
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
    
    print(f"\nConversion complete! {len(json_files)} chunks processed.")
    print(f"Markdown files saved to: {output_dir}")

if __name__ == "__main__":
    convert_json_to_markdown()