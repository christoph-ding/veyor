def validate_job_payload(payload: dict) -> bool:
    """
    STUB: Lightweight validation for incoming job payloads.
    Expand later with strict schema checks (Pydantic / Cerberus).
    """
    if not payload:
        return False
    # TODO (Wide & Shallow): Add deep schema validation for media/probe tasks
    return True