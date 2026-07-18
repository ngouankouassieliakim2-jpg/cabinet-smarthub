"""Document numbering and reference generation."""

class NumberingService:
    """Service for generating document numbers and references."""

    def generate_number(self, prefix: str = "DOC") -> str:
        """Generate a unique document number."""
        raise NotImplementedError
