"""
Prompt Manager

Loads, caches, and renders prompt templates from .md files.

Architecture:
    Business Service → LLMService → PromptManager → Template File → Rendered Prompt

Rules:
- Prompts are NEVER hardcoded in Python files.
- All prompts live in backend/app/prompts/*.md
- Variables are injected using {{variable_name}} syntax.
- Every prompt must include: Purpose, Context, Instructions, Constraints, Output Format.
- Prompts must be versioned.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)

# Default prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptManager:
    """
    Manages all AI prompt templates.

    Loads prompts from .md files on first access (lazy loading).
    Caches loaded prompts in memory.
    Renders templates by substituting {{variable}} placeholders.
    """

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        """
        Initialize the PromptManager.

        Args:
            prompts_dir: Directory containing prompt .md files.
                         Defaults to backend/app/prompts/
        """
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: Dict[str, str] = {}
        logger.info("prompt_manager_initialized", prompts_dir=str(self.prompts_dir))

    def load(self, prompt_name: str) -> str:
        """
        Load a prompt template from disk.

        Args:
            prompt_name: Prompt file name without .md extension (e.g., "entity_extraction")

        Returns:
            Raw prompt template string

        Raises:
            FileNotFoundError: If prompt file does not exist
        """
        if prompt_name in self._cache:
            return self._cache[prompt_name]

        prompt_path = self.prompts_dir / f"{prompt_name}.md"

        if not prompt_path.exists():
            logger.error(
                "prompt_file_not_found",
                prompt_name=prompt_name,
                path=str(prompt_path),
            )
            raise FileNotFoundError(
                f"Prompt template '{prompt_name}.md' not found in {self.prompts_dir}"
            )

        content = prompt_path.read_text(encoding="utf-8")
        self._cache[prompt_name] = content
        logger.info("prompt_loaded", prompt_name=prompt_name)
        return content

    def render(self, prompt_name: str, variables: Dict[str, Any]) -> str:
        """
        Load a prompt template and render it with the provided variables.

        Variables are substituted using {{variable_name}} syntax.

        Args:
            prompt_name: Prompt file name without .md extension
            variables: Dictionary of variable names to values

        Returns:
            Rendered prompt string with variables substituted

        Example:
            render("entity_extraction", {"document_text": "Pump P101 failed..."})
            → replaces {{document_text}} in the template
        """
        template = self.load(prompt_name)

        def replace_variable(match: re.Match) -> str:
            var_name = match.group(1).strip()
            value = variables.get(var_name, f"{{{{MISSING: {var_name}}}}}")
            return str(value)

        rendered = re.sub(r"\{\{([^}]+)\}\}", replace_variable, template)

        logger.info(
            "prompt_rendered",
            prompt_name=prompt_name,
            variables=list(variables.keys()),
        )
        return rendered

    def list_available(self) -> list[str]:
        """
        List all available prompt templates.

        Returns:
            List of prompt names (without .md extension)
        """
        if not self.prompts_dir.exists():
            return []
        return [f.stem for f in self.prompts_dir.glob("*.md")]

    def clear_cache(self) -> None:
        """
        Clear the prompt cache.
        Useful for development when prompts are being edited.
        """
        self._cache.clear()
        logger.info("prompt_cache_cleared")
