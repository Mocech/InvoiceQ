"""
OCR Service — reads text directly from PDF/image files.
No AWS required. Uses pypdf for PDFs and pillow for images.
"""

import logging
import time

logger = logging.getLogger('apps.invoices')


class OCRResult:
    def __init__(self, raw_text, blocks, data_points_found, provider, processing_time_ms):
        self.raw_text           = raw_text
        self.blocks             = blocks
        self.data_points_found  = data_points_found
        self.provider           = provider
        self.processing_time_ms = processing_time_ms


class OCRService:

    def extract(self, file_path: str, file_content_type: str = None) -> OCRResult:
        start = time.time()
        logger.info(f'Starting OCR on {file_path}')

        try:
            raw_text = self._extract_text(file_path, file_content_type)
            elapsed_ms = int((time.time() - start) * 1000)
            lines = [l for l in raw_text.split('\n') if l.strip()]
            logger.info(f'OCR complete in {elapsed_ms}ms, found {len(lines)} lines')
            return OCRResult(
                raw_text=raw_text,
                blocks=[],
                data_points_found=len(lines),
                provider='pypdf',
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            logger.error(f'OCR failed: {e}', exc_info=True)
            return OCRResult(
                raw_text='',
                blocks=[],
                data_points_found=0,
                provider='pypdf',
                processing_time_ms=int((time.time() - start) * 1000),
            )

    def _extract_text(self, file_path: str, content_type: str = None) -> str:
        ext = file_path.lower().split('.')[-1]

        if ext == 'pdf' or (content_type and 'pdf' in content_type):
            return self._extract_pdf(file_path)
        elif ext in ('jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp'):
            return self._extract_image(file_path)
        else:
            # Try PDF first, then image
            try:
                return self._extract_pdf(file_path)
            except Exception:
                return self._extract_image(file_path)

    def _extract_pdf(self, file_path: str) -> str:
        try:
            import pypdf
            text = ''
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
            return text.strip()
        except ImportError:
            # Fallback if pypdf not installed
            try:
                import pdfplumber
                text = ''
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + '\n'
                return text.strip()
            except ImportError:
                logger.warning('Neither pypdf nor pdfplumber installed. Returning empty text.')
                return ''

    def _extract_image(self, file_path: str) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            return pytesseract.image_to_string(img)
        except ImportError:
            logger.warning('pytesseract/PIL not installed. Returning empty text for image.')
            return ''