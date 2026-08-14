import os
import time
from PIL import Image
from minio import Minio

from app.celery_app import celery_app
from app.utils.logger import setup_logger
from app.metadata_db.jobs import update_job_status

logger = setup_logger("veyor-worker")
WORKER_ID = os.getenv("HOSTNAME", "unknown-worker")

# MinIO Client
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "minio-service.backend-veyor.svc.cluster.local:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "quelque_phrase_secret123")

s3_client = Minio(
    S3_ENDPOINT,
    access_key=S3_ACCESS_KEY,
    secret_key=S3_SECRET_KEY,
    secure=False
)


@celery_app.task(name="process_job", bind=True)
def process_job(self, job_id: str, job_type: str, payload: dict):
    start_time = time.time()
    
    logger.info("Started processing job", extra={
        "job_id": job_id,
        "job_type": job_type,
        "worker_id": WORKER_ID
    })

    bucket_name = payload.get("s3_bucket")
    raw_s3_key = payload.get("s3_key")
    processed_key = f"processed/{job_id}_thumb.webp"

    # Temporary disk file paths inside the pod container
    input_tmp_path = f"/tmp/{job_id}_raw"
    output_tmp_path = f"/tmp/{job_id}_thumb.webp"

    try:
        # Mark as RUNNING / PROCESSING in DB
        update_job_status(job_id, "PROCESSING", worker_id=WORKER_ID)

        # 1. Fetch raw asset directly to local disk
        s3_client.fget_object(bucket_name, raw_s3_key, input_tmp_path)

        # 2. Compute Work: Pillow image transformation from disk
        with Image.open(input_tmp_path) as img:
            if getattr(img, "is_animated", False):
                # Preserve animation frames for GIF -> WebP
                img.save(
                    output_tmp_path, 
                    format="WEBP", 
                    save_all=True, 
                    optimize=True,
                    quality=85
                )
            else:
                # Standard static image handling
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((800, 800))
                img.save(output_tmp_path, format="WEBP", quality=85)

        # 3. Upload transformed asset from disk back to MinIO
        s3_client.fput_object(
            bucket_name=bucket_name,
            object_name=processed_key,
            file_path=output_tmp_path,
            content_type="image/webp"
        )

        # 4. Update DB to SUCCESS and merge new processed_s3_key into payload
        update_job_status(
            job_id=job_id, 
            status="SUCCESS", 
            worker_id=WORKER_ID, 
            payload={"processed_s3_key": processed_key}
        )

        duration = time.time() - start_time
        logger.info("Job processing completed successfully", extra={
            "job_id": job_id,
            "duration_seconds": round(duration, 4),
            "worker_id": WORKER_ID,
            "processed_s3_key": processed_key
        })

        return {"status": "SUCCESS", "job_id": job_id, "processed_s3_key": processed_key}

    except Exception as exc:
        duration = time.time() - start_time
        update_job_status(job_id, "FAILED", worker_id=WORKER_ID)
        
        logger.error("Job processing failed", extra={
            "job_id": job_id,
            "error": str(exc),
            "duration_seconds": round(duration, 4),
            "worker_id": WORKER_ID
        })
        raise exc

    finally:
        # Cleanup temporary local files
        for path in (input_tmp_path, output_tmp_path):
            if os.path.exists(path):
                os.remove(path)