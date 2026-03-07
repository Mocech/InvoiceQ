"""
AI Extraction Service — powered by Groq (free, worldwide).
Get your free key at: console.groq.com
Model: llama-3.3-70b-versatile — best Groq model for structured JSON extraction.
Free tier: 14,400 requests/day, 30 requests/min.
"""

import json
import logging
import re
import time

from decouple import config as env_config
from groq import Groq

logger = logging.getLogger('apps.invoices')


EXTRACTION_SYSTEM_PROMPT = """You are an expert invoice data extraction AI for InvoiceIQ, an enterprise finance intelligence platform.

Your job is to extract structured data from invoice OCR text and return it as valid JSON.

IMPORTANT RULES:
1. Return ONLY valid JSON. No markdown, no explanation, no code fences.
2. For every field you extract, include a confidence score between 0.0 and 1.0:
   - 0.90-1.00: Field is clearly present and unambiguous
   - 0.70-0.89: Field found but formatting was unusual or partially unclear
   - 0.50-0.69: Field inferred or partially reconstructed
   - 0.00-0.49: Very uncertain — flag for human review
3. If a field is not found, set its value to null and confidence to 0.0
4. Detect the currency from symbols or text (USD, KES, EUR, GBP, ZAR)
5. Normalize dates to YYYY-MM-DD format
6. For line items, extract each product/service line separately
7. Calculate overall_confidence as the average of all field confidence scores
8. Set needs_human_review to true if any field has confidence < 0.70 or values seem inconsistent
9. If you detect anomalies (duplicate invoice, unusually high amount, missing required fields),
   set flag_message to a concise description

Return this exact JSON structure:
{
  "invoice_number": {"value": "INV-001", "confidence": 0.95},
  "vendor_name": {"value": "ABC Suppliers Ltd", "confidence": 0.92},
  "vendor_address": {"value": "123 Main St, Nairobi", "confidence": 0.88},
  "vendor_email": {"value": "billing@abc.com", "confidence": 0.90},
  "vendor_phone": {"value": "+254 700 000000", "confidence": 0.85},
  "po_number": {"value": "PO-2024-001", "confidence": 0.78},
  "payment_terms": {"value": "Net 30", "confidence": 0.95},
  "invoice_date": {"value": "2024-01-15", "confidence": 0.98},
  "due_date": {"value": "2024-02-15", "confidence": 0.92},
  "currency": {"value": "USD", "confidence": 0.99},
  "subtotal_amount": {"value": "10000.00", "confidence": 0.97},
  "tax_amount": {"value": "1600.00", "confidence": 0.93},
  "total_amount": {"value": "11600.00", "confidence": 0.98},
  "line_items": [
    {
      "description": "Consulting Services",
      "quantity": 1,
      "unit_price": "10000.00",
      "total": "10000.00",
      "confidence": 0.95
    }
  ],
  "overall_confidence": 0.92,
  "needs_human_review": false,
  "flag_message": ""
}"""


class AIExtractionResult:
    def __init__(self, data: dict, raw_response: str, processing_time_ms: int,
                 model_used: str):
        self.data               = data
        self.raw_response       = raw_response
        self.processing_time_ms = processing_time_ms
        self.model_used         = model_used
        self.overall_confidence = data.get('overall_confidence', 0.0)
        self.needs_human_review = data.get('needs_human_review', True)
        self.flag_message       = data.get('flag_message', '')


class AIExtractionService:
    MODEL = 'llama-3.3-70b-versatile'

    def __init__(self):
        self._client = None
        api_key = env_config('GROQ_API_KEY', default='')
        if not api_key:
            logger.warning(
                'GROQ_API_KEY not set in .env — will use mock extraction. '
                'Get a free key at console.groq.com'
            )
        else:
            self._client = Groq(api_key=api_key)
            logger.info(f'Groq client initialised (model: {self.MODEL})')

    def extract(self, ocr_text: str, ocr_blocks: list = None) -> AIExtractionResult:
        if not self._client:
            logger.warning('No Groq client — using mock extraction')
            return self._mock_extraction()
        if not ocr_text or len(ocr_text.strip()) < 20:
            logger.warning('OCR text too short — using mock extraction')
            return self._mock_extraction()

        start = time.time()
        try:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {'role': 'system', 'content': EXTRACTION_SYSTEM_PROMPT},
                    {'role': 'user',   'content': self._build_user_prompt(ocr_text, ocr_blocks)},
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw_response = response.choices[0].message.content
            elapsed_ms   = int((time.time() - start) * 1000)
            data         = self._parse_response(raw_response)

            logger.info(
                f'AI extraction complete in {elapsed_ms}ms, '
                f'confidence={data.get("overall_confidence", 0):.2f}, '
                f'model={self.MODEL}'
            )
            return AIExtractionResult(
                data=data,
                raw_response=raw_response,
                processing_time_ms=elapsed_ms,
                model_used=self.MODEL,
            )
        except Exception as e:
            logger.error(f'AI extraction failed: {e}', exc_info=True)
            return self._mock_extraction()

    def _build_user_prompt(self, ocr_text: str, ocr_blocks: list = None) -> str:
        prompt = f'Extract all invoice data from this OCR text:\n\n---\n{ocr_text}\n---'
        if ocr_blocks:
            kv_pairs = '\n'.join(
                f'{b["key"]}: {b["value"]} (confidence: {b["confidence"]})'
                for b in (ocr_blocks or [])[:50]
            )
            prompt += f'\n\nStructured key-value pairs detected by OCR:\n{kv_pairs}'
        return prompt

    def _parse_response(self, raw_response: str) -> dict:
        text = raw_response.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$',          '', text, flags=re.MULTILINE)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f'Failed to parse Groq JSON: {e}\nRaw: {raw_response[:500]}')
            raise

    def _mock_extraction(self) -> AIExtractionResult:
        mock_data = {
            'invoice_number':  {'value': 'INV-00432',                      'confidence': 0.97},
            'vendor_name':     {'value': 'ABC Suppliers Ltd',               'confidence': 0.95},
            'vendor_address':  {'value': '45 Commerce St, Nairobi, Kenya',  'confidence': 0.82},
            'vendor_email':    {'value': 'billing@abcsuppliers.co.ke',       'confidence': 0.90},
            'vendor_phone':    {'value': '+254 700 123 456',                 'confidence': 0.78},
            'po_number':       {'value': 'PO-2024-0891',                     'confidence': 0.34},
            'payment_terms':   {'value': 'Net 30',                           'confidence': 0.99},
            'invoice_date':    {'value': '2024-01-15',                       'confidence': 0.98},
            'due_date':        {'value': '2024-02-14',                       'confidence': 0.96},
            'currency':        {'value': 'KES',                              'confidence': 0.99},
            'subtotal_amount': {'value': '125000.00',                        'confidence': 0.97},
            'tax_amount':      {'value': '20000.00',                         'confidence': 0.92},
            'total_amount':    {'value': '145000.00',                        'confidence': 0.98},
            'line_items': [
                {'description': 'Office Stationery & Supplies', 'quantity': 10, 'unit_price': '5000.00',  'total': '50000.00',  'confidence': 0.95},
                {'description': 'Printer Cartridges (HP)',       'quantity': 5,  'unit_price': '15000.00', 'total': '75000.00',  'confidence': 0.88},
            ],
            'overall_confidence': 0.87,
            'needs_human_review': True,
            'flag_message': 'PO number confidence is low (34%) — please verify against purchase order.',
        }
        return AIExtractionResult(
            data=mock_data,
            raw_response=json.dumps(mock_data),
            processing_time_ms=850,
            model_used='mock',
        )