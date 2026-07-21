"""
Alias Resolver
"""

import re
from typing import List, Set


class AliasResolver:
    """
    Resolves and normalizes aliases for asset tags and equipment names.
    """

    @staticmethod
    def normalize_tag(name: str) -> str:
        """
        Normalize equipment tags to a standard format.
        Example: "P101", "P 101", "P-101" -> "P-101"
        """
        if not name:
            return ""
        
        # Look for [Letters][Optional Space/Dash][Numbers]
        # e.g., P101, B-02, V 15
        pattern = r"^([A-Za-z]+)[\s\-]*([0-9]+)$"
        match = re.match(pattern, name.strip())
        if match:
            letters = match.group(1).upper()
            numbers = match.group(2)
            return f"{letters}-{numbers}"
            
        return name.strip()

    def deduplicate_aliases(self, label: str, aliases: List[str]) -> List[str]:
        """
        Remove the label from the aliases list, normalize aliases,
        and remove duplicates.
        """
        unique_aliases: Set[str] = set()
        
        for alias in aliases:
            if not alias:
                continue
            # Normalize the alias too
            norm_alias = self.normalize_tag(alias)
            if norm_alias.lower() != label.lower():
                unique_aliases.add(norm_alias)
                # Keep original alias if it's different from normalized to capture variations
                if alias.strip() != norm_alias:
                     unique_aliases.add(alias.strip())
                     
        return sorted(list(unique_aliases))
