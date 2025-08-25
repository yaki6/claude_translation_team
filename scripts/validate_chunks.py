#!/usr/bin/env python3
"""
Chunk validation module with state persistence for PDF generation pipeline.

This module validates markdown chunks for completeness, sequence, and integrity,
while maintaining state for idempotent operations.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ValidationReport:
    """Data structure for validation results."""
    available_chunks: List[int]
    missing_chunks: List[int]
    total_expected: int
    is_valid: bool
    is_partial: bool
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return asdict(self)


class ChunkValidator:
    """Validates markdown chunks with state management for idempotency."""
    
    def __init__(self, chunks_dir: Path, state_dir: Path, expected_total: int = 22):
        """
        Initialize the chunk validator.
        
        Args:
            chunks_dir: Directory containing chunk files
            state_dir: Directory for state persistence
            expected_total: Expected total number of chunks (default: 22)
        """
        self.chunks_dir = Path(chunks_dir)
        self.state_dir = Path(state_dir)
        self.expected_total = expected_total
        self.state_file = self.state_dir / "validation_state.json"
        
        # Ensure directories exist
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_chunk_number(self, filename: str) -> Optional[int]:
        """
        Extract chunk number from filename.
        
        Supports patterns like:
        - chunk_001_final.md
        - chunk_002.md
        - chunk_3_reviewed.md
        """
        match = re.search(r'chunk_(\d+)', filename)
        if match:
            return int(match.group(1))
        return None
    
    def _find_chunk_files(self) -> List[Path]:
        """Find all markdown chunk files in the chunks directory."""
        # Look for chunk files with various patterns
        patterns = [
            "chunk_*.md",
            "chunk_*_final.md",
            "chunk_*_reviewed.md"
        ]
        
        chunk_files = []
        for pattern in patterns:
            chunk_files.extend(self.chunks_dir.glob(pattern))
        
        # Remove duplicates and sort
        unique_files = list(set(chunk_files))
        return sorted(unique_files)
    
    def _validate_file_content(self, file_path: Path) -> bool:
        """
        Validate that a chunk file has valid content.
        
        Returns:
            True if file is valid, False otherwise
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Check if file is empty
            if not content.strip():
                return False
            
            # Check minimum size (at least 10 characters)
            if len(content) < 10:
                return False
            
            return True
            
        except (UnicodeDecodeError, OSError):
            # File is corrupted or has encoding issues
            return False
    
    def _identify_missing_chunks(self, available: List[int]) -> List[int]:
        """
        Identify missing chunk numbers in the sequence.
        
        Args:
            available: List of available chunk numbers
            
        Returns:
            List of missing chunk numbers
        """
        if not available:
            return list(range(1, self.expected_total + 1))
        
        max_chunk = max(available)
        expected_max = max(max_chunk, self.expected_total)
        
        expected_set = set(range(1, expected_max + 1))
        available_set = set(available)
        
        return sorted(list(expected_set - available_set))
    
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Load previous validation state if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None
        return None
    
    def _save_state(self, report: ValidationReport) -> None:
        """Save validation state for idempotency."""
        state_data = {
            "available_chunks": report.available_chunks,
            "missing_chunks": report.missing_chunks,
            "total_expected": report.total_expected,
            "is_valid": report.is_valid,
            "is_partial": report.is_partial,
            "error_message": report.error_message,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
    
    def validate(self) -> ValidationReport:
        """
        Perform chunk validation with state management.
        
        Returns:
            ValidationReport with validation results
        """
        # Find all chunk files
        chunk_files = self._find_chunk_files()
        
        # Check if any chunks found
        if not chunk_files:
            report = ValidationReport(
                available_chunks=[],
                missing_chunks=list(range(1, self.expected_total + 1)),
                total_expected=self.expected_total,
                is_valid=False,
                is_partial=False,
                error_message="No chunks found in directory"
            )
            self._save_state(report)
            return report
        
        # Extract chunk numbers and validate content
        available_chunks = []
        corrupted_files = []
        empty_files = []
        
        for file_path in chunk_files:
            chunk_num = self._extract_chunk_number(file_path.name)
            if chunk_num is None:
                continue
            
            # Validate file content
            if not self._validate_file_content(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if not content.strip():
                        empty_files.append(file_path.name)
                except:
                    corrupted_files.append(file_path.name)
                continue
            
            available_chunks.append(chunk_num)
        
        # Sort available chunks
        available_chunks = sorted(set(available_chunks))
        
        # Check for errors
        if empty_files:
            report = ValidationReport(
                available_chunks=[],
                missing_chunks=[],
                total_expected=self.expected_total,
                is_valid=False,
                is_partial=False,
                error_message=f"Empty chunk file detected: {empty_files[0]}"
            )
            self._save_state(report)
            return report
        
        if corrupted_files:
            report = ValidationReport(
                available_chunks=[],
                missing_chunks=[],
                total_expected=self.expected_total,
                is_valid=False,
                is_partial=False,
                error_message=f"Corrupted or encoding issue in file: {corrupted_files[0]}"
            )
            self._save_state(report)
            return report
        
        # Identify missing chunks
        missing_chunks = self._identify_missing_chunks(available_chunks)
        
        # Determine validation status
        is_valid = len(available_chunks) > 0 and len(missing_chunks) == 0
        is_partial = len(available_chunks) > 0 and len(missing_chunks) > 0
        
        # Update expected total if we found more chunks than expected
        if available_chunks:
            max_found = max(available_chunks)
            total_expected = max(self.expected_total, max_found)
        else:
            total_expected = self.expected_total
        
        # Create report
        report = ValidationReport(
            available_chunks=available_chunks,
            missing_chunks=missing_chunks[:min(len(missing_chunks), total_expected)],
            total_expected=total_expected,
            is_valid=is_valid,
            is_partial=is_partial,
            error_message="" if (is_valid or is_partial) else "Validation failed"
        )
        
        # Save state
        self._save_state(report)
        
        return report


# Standalone functions for backward compatibility
def validate_chunks(
    chunks_dir: Path,
    state_file: Optional[Path] = None,
    total_expected: int = 22
) -> Dict[str, Any]:
    """
    Validate chunks and return a dictionary report.
    
    This function provides backward compatibility with the original API.
    """
    # Determine state directory
    if state_file:
        state_dir = state_file.parent
    else:
        state_dir = Path("data/state")
    
    # Create validator and run validation
    validator = ChunkValidator(
        chunks_dir=chunks_dir,
        state_dir=state_dir,
        expected_total=total_expected
    )
    
    report = validator.validate()
    
    # Convert to dictionary format for backward compatibility
    return {
        'status': 'success' if report.is_valid else ('warning' if report.is_partial else 'error'),
        'available': report.available_chunks,
        'missing': report.missing_chunks,
        'total_expected': report.total_expected,
        'validation_complete': report.is_valid or report.is_partial,
        'error_message': report.error_message
    }


def load_state(state_file: Path) -> Dict[str, Any]:
    """Load validation state from file."""
    state_file = Path(state_file)
    if state_file.exists():
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_state(state_data: Dict[str, Any], state_file: Path) -> None:
    """Save validation state to file."""
    state_file = Path(state_file)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Add timestamp
    state_data['last_updated'] = datetime.now().isoformat()
    
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state_data, f, indent=2)


def check_chunk_sequence(chunks: List[int], expected_total: Optional[int] = None) -> List[int]:
    """Check for gaps in chunk sequence."""
    if not chunks:
        return list(range(1, (expected_total or 1) + 1))
    
    max_chunk = max(chunks)
    if expected_total:
        max_chunk = max(max_chunk, expected_total)
    
    expected = set(range(1, max_chunk + 1))
    actual = set(chunks)
    
    return sorted(list(expected - actual))


def validate_file_sizes(chunk_files: List[Path], min_size: int = 10) -> List[str]:
    """Validate that chunk files have reasonable sizes."""
    issues = []
    
    for file_path in chunk_files:
        try:
            size = file_path.stat().st_size
            if size < min_size:
                issues.append(f"{file_path.name}: File too small ({size} bytes)")
        except:
            issues.append(f"{file_path.name}: Cannot read file")
    
    return issues


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate markdown chunks for PDF generation")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        default=Path("data/reviewed/final"),
        help="Directory containing chunk files"
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path("data/state"),
        help="Directory for state files"
    )
    parser.add_argument(
        "--expected",
        type=int,
        default=22,
        help="Expected number of chunks"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = ChunkValidator(
        chunks_dir=args.chunks_dir,
        state_dir=args.state_dir,
        expected_total=args.expected
    )
    
    report = validator.validate()
    
    # Print results
    print(f"Validation Report")
    print(f"=" * 50)
    print(f"Available chunks: {len(report.available_chunks)}")
    print(f"Missing chunks: {len(report.missing_chunks)}")
    print(f"Total expected: {report.total_expected}")
    print(f"Status: {'✅ Valid' if report.is_valid else '⚠️ Partial' if report.is_partial else '❌ Invalid'}")
    
    if report.available_chunks:
        print(f"\nAvailable: {report.available_chunks[:10]}{'...' if len(report.available_chunks) > 10 else ''}")
    
    if report.missing_chunks and len(report.missing_chunks) <= 10:
        print(f"Missing: {report.missing_chunks}")
    
    if report.error_message:
        print(f"\nError: {report.error_message}")
    
    return 0 if report.is_valid or report.is_partial else 1


if __name__ == "__main__":
    exit(main())