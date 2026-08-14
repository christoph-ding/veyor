import json
from app.metadata_db.connection import get_connection

def create_job_record(job_id: str, job_type: str, payload: dict) -> None:
    """Write initial PENDING metadata state to Postgres."""
    query = """
    INSERT INTO jobs (job_id, job_type, status, payload)
    VALUES (%s, %s, %s, %s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (job_id, job_type, "PENDING", json.dumps(payload)))

def update_job_status(job_id: str, status: str, worker_id: str = None, payload: dict = None) -> None:
    """Update job status (PROCESSING, SUCCESS, FAILED), record worker_id, and optionally update payload."""
    query = """
    UPDATE jobs
    SET status = %s,
        worker_id = COALESCE(%s, worker_id),
        payload = CASE WHEN %s::jsonb IS NOT NULL THEN payload || %s::jsonb ELSE payload END,
        updated_at = CURRENT_TIMESTAMP
    WHERE job_id = %s;
    """
    payload_json = json.dumps(payload) if payload else None
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (status, worker_id, payload_json, payload_json, job_id))

def get_job_record(job_id: str):
    """
    Fetch a single job record from Postgres by job_id.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT job_id, job_type, status, payload, worker_id, created_at, updated_at
                FROM jobs
                WHERE job_id = %s;
                """,
                (job_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "job_id": row[0],
                "job_type": row[1],
                "status": row[2],
                "payload": row[3],
                "worker_id": row[4],
                "created_at": row[5],
                "updated_at": row[6]
            }