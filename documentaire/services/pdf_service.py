"""PDF creation and transformation utilities."""

class PDFService:
    """Wrapper for PDF generation and manipulation."""

    def generate_pdf(self, html_content: str, output_path: str) -> str:
        """Generate a PDF file from HTML content."""
        raise NotImplementedError

    def merge_pdfs(self, input_paths: list[str], output_path: str) -> str:
        """Merge multiple PDF files into a single PDF."""
        raise NotImplementedError
