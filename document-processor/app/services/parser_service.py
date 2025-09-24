import re
from typing import Any, Dict

from ..models import ParsedData


class ParserService:
    def parse(self, document_type: str, text: str) -> ParsedData:
        document_type = document_type.lower()
        fields: Dict[str, Any] = {}
        validation_errors = []
        confidence = 0.5

        if document_type in {"invoice", "receipt"}:
            amount_match = re.search(r"(?i)(total|amount)[:\s\$]*([0-9]+(?:\.[0-9]{2})?)", text)
            date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text)
            vendor_match = re.search(r"(?i)(from|vendor|seller)[:\s]+([A-Za-z0-9 &,-]{3,})", text)
            if amount_match:
                fields["total_amount"] = float(amount_match.group(2))
                confidence += 0.2
            if date_match:
                fields["date"] = date_match.group(1)
                confidence += 0.1
            if vendor_match:
                fields["vendor"] = vendor_match.group(2).strip()
                confidence += 0.1
            if not fields:
                validation_errors.append("No fields extracted")
        elif document_type == "contract":
            party_match = re.findall(r"(?i)(between|by and between)\s+([A-Za-z0-9 &,-]{3,})", text)
            term_match = re.search(r"(?i)term[:\s]+(\d+\s+(months?|years?))", text)
            if party_match:
                fields["parties"] = [m[1].strip() for m in party_match]
                confidence += 0.2
            if term_match:
                fields["term"] = term_match.group(1)
                confidence += 0.1
            if not fields:
                validation_errors.append("No fields extracted")
        else:
            validation_errors.append("Unsupported parser type")

        confidence = min(max(confidence, 0.0), 1.0)
        return ParsedData(
            document_type=document_type,
            fields=fields,
            validation_errors=validation_errors,
            parsing_confidence=confidence,
        )

