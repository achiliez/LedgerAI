"""
LedgerAI — Privacy Module
Uses Microsoft Presidio to mask PII before sending messages to cloud LLMs.
"""

import logging

logger = logging.getLogger(__name__)

# Presidio is optional — if not installed, messages pass through unmasked.
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()
    PRESIDIO_AVAILABLE = True
    logger.info("✅ Presidio loaded — PII masking enabled")
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning(
        "⚠️  Presidio not installed — PII masking disabled. "
        "Install with: pip install presidio-analyzer presidio-anonymizer spacy && "
        "python -m spacy download en_core_web_lg"
    )


# Entity types we want to detect and mask
_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
]


def mask_pii(text: str) -> str:
    """
    Mask personally identifiable information in the input text.
    Returns the anonymized text, or the original text if Presidio is unavailable.

    Example:
        "John paid ₹500 to merchant via card 4111-1111-1111-1111"
        → "<PERSON> paid ₹500 to merchant via card <CREDIT_CARD>"
    """
    if not PRESIDIO_AVAILABLE:
        return text

    try:
        results = _analyzer.analyze(
            text=text,
            entities=_ENTITIES,
            language="en",
        )
        anonymized = _anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
    except Exception as e:
        logger.error(f"PII masking failed, using original text: {e}")
        return text
