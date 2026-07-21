"""
Synonym Resolver
"""

from typing import Dict, List, Optional
from app.ontology.constants import ENTITY_SYNONYMS


class SynonymResolver:
    """
    Resolves entity labels and types to their canonical ontology forms.
    Uses string matching and predefined rules.
    """

    def __init__(self) -> None:
        # Build reverse mapping for O(1) lookups: {synonym.lower(): canonical}
        self._reverse_map: Dict[str, str] = {}
        for canonical, synonyms in ENTITY_SYNONYMS.items():
            for syn in synonyms:
                self._reverse_map[syn.lower()] = canonical

    def resolve_label(self, label: str) -> str:
        """
        Resolve an entity label to its canonical synonym if one exists.
        For example, "Water Pump" -> "Pump".
        If no synonym is found, returns the original label (capitalized properly).
        """
        if not label:
            return ""
        
        normalized = label.strip().lower()
        if normalized in self._reverse_map:
            return self._reverse_map[normalized]
        
        # If no mapping, just clean up spacing and title case if it's purely alphabetical
        if label.replace(" ", "").isalpha():
            return label.title()
        return label.strip()

    def resolve_type(self, entity_type: str) -> str:
        """
        Resolve entity type to core types if possible, or return as is.
        """
        # Very basic normalization for types
        return entity_type.strip().title()
