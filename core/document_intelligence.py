"""
Warehouse Document Intelligence & Text Parsing Service (Service 11)
Extracts structured logistics entities (Trailer ID, Carrier, Appointment, Dock Door,
Delay Reasons, Temperature, Cut-off times) from carrier emails, delay notes, BOLs, and shift logs.
"""

from typing import Dict, Any, Optional
import re
import uuid
from core.models import DocumentExtractionResult

class DocumentIntelligenceService:
    def __init__(self):
        # Common regex patterns for warehouse logistics documents
        self.trailer_pattern = re.compile(r'\b(?:TRAILER|CONTAINER|CNTR|TRL|TR)[-:\s]+([A-Z0-9]{3,10})\b', re.IGNORECASE)
        self.appt_pattern = re.compile(r'\b(?:APPOINTMENT|APPT|APT)[-:\s]+([A-Z0-9]{3,10})\b', re.IGNORECASE)
        self.door_pattern = re.compile(r'\b(?:DOCK|DOOR)[-:\s]+([0-9]{1,2}|[A-Z]-[0-9]{1,2})\b', re.IGNORECASE)
        self.time_pattern = re.compile(r'\b(?:[01]?[0-9]|2[0-3]):[0-5][0-9]\b')
        self.temp_pattern = re.compile(r'(-?\d{1,2}(?:\.\d+)?)\s*(?:°|deg|degrees)?\s*([CF])\b', re.IGNORECASE)
        self.carrier_keywords = ["J.B. Hunt", "Swift", "Schneider", "Knight", "Werner", "XPO", "Old Dominion", "FedEx", "UPS", "DHL", "CH Robinson"]


    def extract_document(self, text: str, document_type: str = "AUTO") -> DocumentExtractionResult:
        """
        Extracts structured operational entities from unstructured text.
        """
        extracted: Dict[str, Any] = {}
        confidence = 0.5

        # Infer document type if AUTO
        upper_text = text.upper()
        if document_type == "AUTO":
            if "APPOINTMENT" in upper_text or "DELIVERY SLOT" in upper_text:
                document_type = "APPOINTMENT_EMAIL"
            elif "DELAY" in upper_text or "LATE" in upper_text or "BREAKDOWN" in upper_text or "DETENTION" in upper_text:
                document_type = "CARRIER_DELAY_NOTE"
            elif "BOL" in upper_text or "BILL OF LADING" in upper_text:
                document_type = "BOL"
            else:
                document_type = "SHIFT_HANDOVER"

        # 1. Trailer extraction
        trailer_match = self.trailer_pattern.search(text)
        if trailer_match:
            extracted["trailer_id"] = f"TR-{trailer_match.group(1).upper()}"
            confidence += 0.15

        # 2. Appointment extraction
        appt_match = self.appt_pattern.search(text)
        if appt_match:
            extracted["appointment_id"] = f"APT-{appt_match.group(1).upper()}"
            confidence += 0.15

        # 3. Dock Door extraction
        door_match = self.door_pattern.search(text)
        if door_match:
            extracted["dock_door"] = f"DOOR-{door_match.group(1).upper()}"
            confidence += 0.10

        # 4. Carrier detection
        detected_carrier = None
        for carrier in self.carrier_keywords:
            if carrier.lower() in text.lower():
                detected_carrier = carrier
                break
        if detected_carrier:
            extracted["carrier"] = detected_carrier
            confidence += 0.10

        # 5. Times / ETA extraction
        times = self.time_pattern.findall(text)
        if times:
            extracted["time_references"] = times
            confidence += 0.05

        # 6. Temperature requirement
        temp_match = self.temp_pattern.search(text)
        if temp_match:
            extracted["temperature_controlled"] = True
            extracted["target_temperature"] = f"{temp_match.group(1)} {temp_match.group(2).upper()}"
            confidence += 0.10
        elif "REEFER" in upper_text or "FROZEN" in upper_text or "CHILLED" in upper_text:
            extracted["temperature_controlled"] = True
            extracted["temperature_zone"] = "COLD_CHAIN"

        # 7. Delay keywords
        delay_reasons = []
        if "TRAFFIC" in upper_text or "CONGESTION" in upper_text:
            delay_reasons.append("Highway traffic congestion")
        if "WEATHER" in upper_text or "SNOW" in upper_text or "STORM" in upper_text:
            delay_reasons.append("Severe weather conditions")
        if "MECHANICAL" in upper_text or "FLAT TIRE" in upper_text or "BREAKDOWN" in upper_text:
            delay_reasons.append("Mechanical equipment failure")
        if "DETENTION" in upper_text:
            delay_reasons.append("Detention clock warning")

        if delay_reasons:
            extracted["delay_reasons"] = delay_reasons
            extracted["is_delay_reported"] = True
            confidence += 0.10

        # Determine if immediate action is required
        action_required = (
            document_type in ["CARRIER_DELAY_NOTE", "APPOINTMENT_EMAIL"]
            or "URGENT" in upper_text
            or "ASAP" in upper_text
            or "DETENTION" in upper_text
        )

        clarification = None
        if not trailer_match and not appt_match:
            clarification = "Neither Trailer ID nor Appointment ID could be reliably matched from text."
            confidence = max(0.35, confidence - 0.20)

        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

        return DocumentExtractionResult(
            document_id=doc_id,
            document_type=document_type,
            confidence_score=min(0.98, round(confidence, 2)),
            extracted_fields=extracted,
            matched_entity_id=extracted.get("appointment_id") or extracted.get("trailer_id"),
            action_required=action_required,
            clarification_needed=clarification
        )

document_service = DocumentIntelligenceService()
