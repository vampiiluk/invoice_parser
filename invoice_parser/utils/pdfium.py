import pypdfium2 as pdfium
import logging

logger = logging.getLogger(__name__)

def to_text(path):
    try:
        pdf = pdfium.PdfDocument(path)
        text = ""
        for page in pdf:
            textpage = page.get_textpage()
            text += textpage.get_text_range() + "\n"
        return text.encode('utf-8')
    except Exception as e:
        logger.error(f"pdfium extraction failed: {e}")
        return b""
