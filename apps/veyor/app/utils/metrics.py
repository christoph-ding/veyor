from prometheus_client import Counter

# Job Lifecycle Counters (Used by FastAPI Gateway)
JOBS_SUBMITTED_TOTAL = Counter(
    "veyor_jobs_submitted_total", 
    "Total jobs submitted through the API gateway", 
    ["job_type"]
)