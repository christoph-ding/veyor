import os
import uuid
from datetime import timedelta

from fastapi import FastAPI, HTTPException, status, UploadFile, File, Form, HTTPException, status
from minio import Minio

from app.utils.logger import setup_logger
from app.utils.prometheus import init_api_metrics
from app.utils.metrics import JOBS_SUBMITTED_TOTAL
from app.utils.validators import validate_job_payload
from app.metadata_db.connection import init_db
from app.metadata_db.jobs import create_job_record, get_job_record
from app.tasks import process_job

logger = setup_logger("veyor-api")

app = FastAPI(title="Veyor API Gateway", version="1.0.0")
# Auto-instrument FastAPI with standard HTTP metrics (latency, request counts)
init_api_metrics(app, endpoint="/metrics")


# ------------------------------------------------------------------
# MinIO S3 Client Setup
# ------------------------------------------------------------------
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "minio-service.backend-veyor.svc.cluster.local:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "quelque_phrase_secret123")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "veyor-media")
RAW_FOLDER = "raw"


s3_client = Minio(
    S3_ENDPOINT,
    access_key=S3_ACCESS_KEY,
    secret_key=S3_SECRET_KEY,
    secure=False  # HTTP inside cluster
)

@app.on_event("startup")
def startup_event():
    init_db()
    # Ensure S3 storage bucket exists on start
    try:
        if not s3_client.bucket_exists(BUCKET_NAME):
            s3_client.make_bucket(BUCKET_NAME)
    except Exception as e:
        print(f"[WARN] S3 Bucket init failed or pending: {e}")


@app.post("/jobs", status_code=status.HTTP_201_CREATED)
def submit_job(
    job_type: str = Form(...),
    file: UploadFile = File(...)
    ):
    
    # def rename_reserved_keys(logger, method_name, event_dict):
    # # Python reserved LogRecord attributes
    # reserved = ["filename", "name", "msg", "args", "asctime", "levelname", "levelno", "lineno"]
    # 
    # for key in reserved:
    #     if key in event_dict:
    #         # Rename 'filename' to 'log_filename' or similar
    #         event_dict[f"log_{key}"] = event_dict.pop(key)
            
    # return event_dict
    

    # 0. Structured JSON log on arrival
    logger.info("Received job submission", extra={
        "file_name": file.filename,
        "job_type": job_type,
        "content_type": file.content_type
    })

    # 1. Assign Job ID & Derive S3 Key
    job_id = str(uuid.uuid4())
    object_key = f"{RAW_FOLDER}/{job_id}_{file.filename}"

    # Construct the payload dictionary
    payload = {
        "s3_bucket": BUCKET_NAME,
        "s3_key": object_key,
        "filename": file.filename,
        "content_type": file.content_type
    }

    # 2. Validate Payload Structure FIRST (Fail Fast!)
    if not validate_job_payload(payload):
        raise HTTPException(status_code=400, detail="Invalid job payload structure")

    # 3. Stream File Bytes to MinIO (Data at Rest)
    try:
        s3_client.put_object(
            bucket_name=BUCKET_NAME,
            object_name=object_key,
            data=file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stream asset to MinIO: {str(e)}"
        )

    # 4. Write 'PENDING' to Metadata DB
    try:
        create_job_record(job_id=job_id, job_type=job_type, payload=payload)
    except Exception as e:
        # TODO: Cleanup MinIO object if DB write fails!
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to record metadata: {str(e)}"
        )

    # 5. Push Task to Redis Queue
    try:
        process_job.delay(job_id=job_id, job_type=job_type, payload=payload)
    except Exception as e:
        # TODO (Wide & Shallow): Handle DB status update to 'FAILED' if enqueue fails
        raise HTTPException(
            status_code=500,
            detail=f"Failed to push task to queue: {str(e)}"
        )

    # 6. Increment Prometheus Counter
    JOBS_SUBMITTED_TOTAL.labels(job_type=job_type).inc()

    logger.info("Successfully enqueued job", extra={
        "job_id": job_id,
        "job_type": job_type
    })

    return {
        "job_id": job_id,
        "status": "PENDING",
        "s3_key": object_key,
        "message": "Asset stored in MinIO, metadata recorded, and task queued successfully."
    }


@app.get("/jobs/{job_id}", status_code=status.HTTP_200_OK)
def get_job_status(job_id: str):
    """
    Retrieve status and metadata for a specific job.
    """
    job = get_job_record(job_id)
    if not job:
        raise HTTPException(
            status_code=404, 
            detail=f"Job '{job_id}' not found."
        )
    return job

@app.get("/jobs/{job_id}/download", status_code=status.HTTP_200_OK)
def get_job_download_url(job_id: str):
    """
    returns a presigned url for direct retrieval of object from S3
    """
    #1. Fetch job record
    job = get_job_record(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"job is not ready for download. current status: {job['status']}"

        )

    # Generate Presigned URL (valid for some time)
    try:
        s3_key = job.get("payload", {}).get("s3_key")

        if not s3_key:  
            raise HTTPException(status_code=400, detail="No S3 key found for this job payload.")

        url = s3_client.presigned_get_object(
            bucket_name="veyor-media",
            object_name=s3_key,
            expires=timedelta(minutes=60)
        )
        return {
            "job_id": job_id,
            "download_url": url,
            "expires_in_seconds": 900
        }
    except Exception as e:
        logger.error("Failed to generate presigned URL", extra={"job_id": job_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Could not generate download link")
    