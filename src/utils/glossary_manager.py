"""Custom glossary management for transcription services."""

from pathlib import Path
from typing import List, Dict, Any, Set, Optional
import re

from .exceptions import GlossaryError


class GlossaryManager:
    """Manages custom glossary terms for transcription services."""
    
    MAX_TERMS = 1000
    MIN_TERM_LENGTH = 2
    MAX_TERM_LENGTH = 50
    
    def __init__(self, warn_on_truncation: bool = True):
        self.warn_on_truncation = warn_on_truncation
        self.loaded_terms: List[str] = []
        self.source_files: List[Path] = []
    
    def load_glossary_file(self, file_path: Path) -> List[str]:
        """Load glossary terms from a single text file (one term per line)."""
        if not file_path.exists():
            raise GlossaryError(f"Glossary file does not exist: {file_path}")
        
        if not file_path.is_file():
            raise GlossaryError(f"Glossary path is not a file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            terms = []
            for line_num, line in enumerate(lines, 1):
                term = line.strip()
                
                # Skip empty lines and comments
                if not term or term.startswith('#'):
                    continue
                
                # Validate term
                validation_result = self.validate_term(term)
                if validation_result['is_valid']:
                    terms.append(validation_result['normalized_term'])
                else:
                    print(f"Warning: Invalid term on line {line_num} in {file_path}: {term} - {validation_result['error']}")
            
            return terms
        
        except IOError as e:
            raise GlossaryError(f"Cannot read glossary file {file_path}: {e}")
        except UnicodeDecodeError as e:
            raise GlossaryError(f"Cannot decode glossary file {file_path}: {e}")
    
    def load_multiple_glossaries(self, file_paths: List[Path]) -> List[str]:
        """Load and merge terms from multiple glossary files."""
        all_terms = []
        self.source_files = []
        
        for file_path in file_paths:
            try:
                terms = self.load_glossary_file(file_path)
                all_terms.extend(terms)
                self.source_files.append(file_path)
                print(f"Loaded {len(terms)} terms from {file_path}")
            except GlossaryError as e:
                print(f"Error loading glossary {file_path}: {e}")
                continue
        
        # Remove duplicates while preserving order
        unique_terms = []
        seen = set()
        for term in all_terms:
            term_lower = term.lower()
            if term_lower not in seen:
                unique_terms.append(term)
                seen.add(term_lower)
        
        # Apply term limit
        if len(unique_terms) > self.MAX_TERMS:
            if self.warn_on_truncation:
                print(f"Warning: Glossary contains {len(unique_terms)} terms, truncating to {self.MAX_TERMS}")
            unique_terms = unique_terms[:self.MAX_TERMS]
        
        self.loaded_terms = unique_terms
        return unique_terms
    
    def validate_term(self, term: str) -> Dict[str, Any]:
        """Validate a single glossary term."""
        result = {
            'is_valid': True,
            'normalized_term': term.strip(),
            'error': None
        }
        
        # Basic validation
        if not term or not term.strip():
            result['is_valid'] = False
            result['error'] = "Empty term"
            return result
        
        normalized = term.strip()
        
        # Length validation
        if len(normalized) < self.MIN_TERM_LENGTH:
            result['is_valid'] = False
            result['error'] = f"Term too short (minimum {self.MIN_TERM_LENGTH} characters)"
            return result
        
        if len(normalized) > self.MAX_TERM_LENGTH:
            result['is_valid'] = False
            result['error'] = f"Term too long (maximum {self.MAX_TERM_LENGTH} characters)"
            return result
        
        # Character validation - allow letters, numbers, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z0-9\s\-'\.]+$", normalized):
            result['is_valid'] = False
            result['error'] = "Term contains invalid characters"
            return result
        
        # No leading/trailing spaces or special characters
        if normalized != normalized.strip():
            result['normalized_term'] = normalized.strip()
        
        return result
    
    def get_rbti_default_terms(self) -> List[str]:
        """Get default RBTI (Reams Biological Theory of Ionization) terminology."""
        rbti_terms = [
            # Core RBTI concepts
            "RBTI", "Reams Biological Theory of Ionization",
            "Carey Reams", "Dr. Carey Reams",
            "biological ionization", "ionization",
            
            # RBTI measurements
            "urine pH", "saliva pH", "conductivity",
            "cell debris", "nitrate nitrogen", "ammonia nitrogen",
            "total carbohydrate", "brix reading",
            
            # RBTI terminology
            "cation", "anion", "milhouse",
            "resistance", "conductance", "ohms",
            "refractometer", "pH meter",
            
            # Health concepts
            "biological age", "energy level",
            "mineral deficiency", "enzyme activity",
            "cellular energy", "metabolic efficiency",
            
            # RBTI ranges and values
            "perfect range", "ideal numbers",
            "energy range", "healing range",
            "zone one", "zone two", "zone three",
            
            # Common supplements mentioned
            "calcium", "magnesium", "potassium",
            "phosphorus", "manganese", "iron",
            "vitamin C", "lemon water",
            
            # RBTI practitioners and locations
            "Reams Institute", "biological consultant",
            "RBTI practitioner", "energy consultant"
        ]
        
        return rbti_terms
    
    def create_default_glossary_file(self, output_path: Path) -> None:
        """Create a default RBTI glossary file."""
        default_terms = self.get_rbti_default_terms()
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# RBTI (Reams Biological Theory of Ionization) Glossary\n")
                f.write("# One term per line, lines starting with # are comments\n\n")
                
                for term in default_terms:
                    f.write(f"{term}\n")
            
            print(f"Created default RBTI glossary with {len(default_terms)} terms at {output_path}")
        
        except IOError as e:
            raise GlossaryError(f"Cannot create glossary file {output_path}: {e}")
    
    def get_terms_for_service(self, service: str) -> List[str]:
        """Get formatted terms for specific transcription service."""
        if not self.loaded_terms:
            return []
        
        # Deepgram uses keywords format
        return self.loaded_terms[:1000]  # Enforce limit
    
    def get_glossary_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded glossary."""
        if not self.loaded_terms:
            return {
                'total_terms': 0,
                'source_files': 0,
                'is_truncated': False,
                'files': []
            }
        
        return {
            'total_terms': len(self.loaded_terms),
            'source_files': len(self.source_files),
            'is_truncated': len(self.loaded_terms) >= self.MAX_TERMS,
            'files': [str(f) for f in self.source_files],
            'sample_terms': self.loaded_terms[:10]  # First 10 terms as sample
        }
    
    def export_glossary(self, output_path: Path, include_stats: bool = True) -> None:
        """Export current glossary to a file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if include_stats:
                    stats = self.get_glossary_stats()
                    f.write(f"# Exported Glossary - {stats['total_terms']} terms\n")
                    f.write(f"# Source files: {', '.join(stats['files'])}\n\n")
                
                for term in self.loaded_terms:
                    f.write(f"{term}\n")
        
        except IOError as e:
            raise GlossaryError(f"Cannot export glossary to {output_path}: {e}")