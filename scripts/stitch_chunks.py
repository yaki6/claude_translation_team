#!/usr/bin/env python3
"""
Chunk stitching module with idempotency for PDF generation pipeline.

This module consolidates multiple markdown chunks into a single file
while maintaining state for resumable operations.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
import natsort


@dataclass
class StitchingResult:
    """Result of the stitching operation."""
    success: bool
    processed_chunks: List[int]
    missing_chunks: List[int]
    output_file: Optional[str]
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class StitchingState:
    """State tracking for idempotent stitching."""
    processed_chunks: List[int]
    last_chunk: Optional[int]
    completed: bool
    output_file: str
    checksum: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StitchingState':
        """Create from dictionary."""
        return cls(**data)


class ChunkStitcher:
    """Stitches markdown chunks with state management for idempotency."""
    
    def __init__(
        self, 
        chunks_dir: Path,
        output_dir: Path,
        state_dir: Path,
        separator: str = "\n\n---\n\n",
        skip_missing: bool = True,
        skip_corrupted: bool = True
    ):
        """
        Initialize the chunk stitcher.
        
        Args:
            chunks_dir: Directory containing chunk files
            output_dir: Directory for output file
            state_dir: Directory for state persistence
            separator: Text to insert between chunks
            skip_missing: Whether to skip missing chunks (vs error)
            skip_corrupted: Whether to skip corrupted chunks
        """
        self.chunks_dir = Path(chunks_dir)
        self.output_dir = Path(output_dir)
        self.state_dir = Path(state_dir)
        self.separator = separator
        self.skip_missing = skip_missing
        self.skip_corrupted = skip_corrupted
        self.state_file = self.state_dir / "stitching_state.json"
        
        # Ensure directories exist
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_chunk_number(self, filename: str) -> Optional[int]:
        """Extract chunk number from filename."""
        match = re.search(r'chunk_(\d+)', filename)
        if match:
            return int(match.group(1))
        return None
    
    def _find_chunk_files(self) -> List[Path]:
        """Find all markdown chunk files in the chunks directory."""
        patterns = [
            "chunk_*.md",
            "chunk_*_final.md",
            "chunk_*_reviewed.md"
        ]
        
        chunk_files = []
        for pattern in patterns:
            chunk_files.extend(self.chunks_dir.glob(pattern))
        
        # Remove duplicates and sort naturally
        unique_files = list(set(chunk_files))
        return natsort.natsorted(unique_files)
    
    def _read_chunk_content(self, file_path: Path) -> Optional[str]:
        """
        Read content from a chunk file.
        
        Returns:
            Content string or None if file is corrupted
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            if content.strip():
                return content
            return None
        except (UnicodeDecodeError, OSError) as e:
            print(f"Error reading {file_path.name}: {e}")
            return None
    
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Load previous stitching state if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None
        return None
    
    def _save_state(self, state_data: Dict[str, Any]) -> None:
        """Save stitching state for idempotency."""
        state_data['timestamp'] = datetime.now().isoformat()
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate MD5 checksum of content."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _create_missing_chunk_placeholder(self, chunk_num: int) -> str:
        """Create placeholder text for missing chunk."""
        return f"\n\n<!-- MISSING CHUNK: chunk_{chunk_num:03d} -->\n\n[章节 {chunk_num} 缺失 / Chapter {chunk_num} missing]\n\n"
    
    def _create_error_placeholder(self, chunk_num: int, error: str) -> str:
        """Create placeholder text for corrupted chunk."""
        return f"\n\n<!-- ERROR IN CHUNK: chunk_{chunk_num:03d} -->\n\n[章节 {chunk_num} 读取错误 / Error reading chapter {chunk_num}: {error}]\n\n"
    
    def stitch_chunks(self) -> StitchingResult:
        """
        Perform chunk stitching with state management.
        
        Returns:
            StitchingResult with operation details
        """
        # Check for existing state
        existing_state = self._load_state()
        
        # If completed, return existing result
        if existing_state and existing_state.get('completed'):
            output_file = Path(existing_state['output_file'])
            if output_file.exists():
                print(f"Stitching already completed. Output: {output_file}")
                return StitchingResult(
                    success=True,
                    processed_chunks=existing_state['processed_chunks'],
                    missing_chunks=existing_state.get('missing_chunks', []),
                    output_file=str(output_file)
                )
        
        # Find all chunk files
        chunk_files = self._find_chunk_files()
        
        if not chunk_files:
            error_msg = "No chunks found in directory"
            return StitchingResult(
                success=False,
                processed_chunks=[],
                missing_chunks=[],
                output_file=None,
                error_message=error_msg
            )
        
        # Extract and sort chunk numbers
        chunk_map = {}
        for file_path in chunk_files:
            chunk_num = self._extract_chunk_number(file_path.name)
            if chunk_num and chunk_num not in chunk_map:
                chunk_map[chunk_num] = file_path
        
        if not chunk_map:
            return StitchingResult(
                success=False,
                processed_chunks=[],
                missing_chunks=[],
                output_file=None,
                error_message="No valid chunk files found"
            )
        
        # Determine output file path
        output_file = self.output_dir / "consolidated.md"
        
        # Determine chunks to process
        all_chunk_nums = sorted(chunk_map.keys())
        max_chunk = max(all_chunk_nums)
        expected_chunks = list(range(1, max_chunk + 1))
        missing_chunks = [n for n in expected_chunks if n not in chunk_map]
        
        # Process chunks in order
        processed_chunks = []
        consolidated_content = []
        
        # If resuming, load existing content
        if existing_state and not existing_state.get('completed'):
            processed_chunks = existing_state.get('processed_chunks', [])
            if output_file.exists() and processed_chunks:
                # Read existing content up to last processed chunk
                consolidated_content = [output_file.read_text(encoding='utf-8')]
        
        # Process each expected chunk
        for chunk_num in expected_chunks:
            # Skip if already processed
            if chunk_num in processed_chunks:
                continue
            
            if chunk_num in chunk_map:
                # Read and add chunk content
                file_path = chunk_map[chunk_num]
                content = self._read_chunk_content(file_path)
                
                if content:
                    # Add separator if not first chunk
                    if consolidated_content:
                        consolidated_content.append(self.separator)
                    consolidated_content.append(content)
                    processed_chunks.append(chunk_num)
                    print(f"Processed chunk {chunk_num:03d}")
                elif self.skip_corrupted:
                    # Add error placeholder
                    consolidated_content.append(
                        self._create_error_placeholder(chunk_num, "Cannot read file")
                    )
                    print(f"Skipped corrupted chunk {chunk_num:03d}")
                else:
                    # Fail on corrupted chunk
                    return StitchingResult(
                        success=False,
                        processed_chunks=processed_chunks,
                        missing_chunks=missing_chunks,
                        output_file=None,
                        error_message=f"Corrupted chunk: {file_path.name}"
                    )
            elif self.skip_missing:
                # Add placeholder for missing chunk
                consolidated_content.append(
                    self._create_missing_chunk_placeholder(chunk_num)
                )
                print(f"Added placeholder for missing chunk {chunk_num:03d}")
            else:
                # Fail on missing chunk
                return StitchingResult(
                    success=False,
                    processed_chunks=processed_chunks,
                    missing_chunks=missing_chunks,
                    output_file=None,
                    error_message=f"Missing chunk: chunk_{chunk_num:03d}"
                )
            
            # Save intermediate state
            self._save_state({
                'processed_chunks': processed_chunks,
                'last_processed_chunk': chunk_num,
                'output_file': str(output_file),
                'total_chunks_found': len(chunk_map),
                'missing_chunks': missing_chunks,
                'completed': False
            })
        
        # Write consolidated content
        final_content = ''.join(consolidated_content)
        output_file.write_text(final_content, encoding='utf-8')
        
        # Calculate checksum
        checksum = self._calculate_checksum(final_content)
        
        # Save final state
        self._save_state({
            'processed_chunks': processed_chunks,
            'missing_chunks': missing_chunks,
            'output_file': str(output_file),
            'checksum': checksum,
            'completed': True,
            'total_chunks': max_chunk,
            'chunks_found': len(chunk_map)
        })
        
        print(f"\nStitching completed successfully!")
        print(f"Processed chunks: {len(processed_chunks)}")
        print(f"Missing chunks: {len(missing_chunks)}")
        print(f"Output file: {output_file}")
        
        return StitchingResult(
            success=True,
            processed_chunks=processed_chunks,
            missing_chunks=missing_chunks,
            output_file=str(output_file)
        )
    
    def stitch(self) -> Path:
        """
        Simplified API for backward compatibility.
        
        Returns:
            Path to the output file
        """
        result = self.stitch_chunks()
        if result.success:
            return Path(result.output_file)
        else:
            raise RuntimeError(f"Stitching failed: {result.error_message}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stitch markdown chunks into consolidated file")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/reviewed/final"),
        help="Directory containing chunk files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/output"),
        help="Directory for output file"
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("data/state"),
        help="Directory for state files"
    )
    parser.add_argument(
        "--separator",
        type=str,
        default="\n\n---\n\n",
        help="Separator between chunks"
    )
    parser.add_argument(
        "--no-skip-missing",
        action="store_true",
        help="Fail on missing chunks instead of using placeholders"
    )
    
    args = parser.parse_args()
    
    # Run stitching
    stitcher = ChunkStitcher(
        chunks_dir=args.chunks_dir,
        output_dir=args.output_dir,
        state_dir=args.state_dir,
        separator=args.separator,
        skip_missing=not args.no_skip_missing
    )
    
    result = stitcher.stitch_chunks()
    
    if result.success:
        print(f"\n✅ Success! Output: {result.output_file}")
        return 0
    else:
        print(f"\n❌ Failed: {result.error_message}")
        return 1


if __name__ == "__main__":
    exit(main())