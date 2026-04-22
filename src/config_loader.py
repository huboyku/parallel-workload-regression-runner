import yaml
from .models import JobConfig

def load_jobs_from_yaml(config_path: str) -> list[JobConfig]:
    with open(config_path) as f:
        config = yaml.safe_load(f)

    jobs = config["jobs"]
    
    job_configs = []
    for job in jobs: 
        job_config = JobConfig(
            name = job["name"],
            command = job["command"],
            expected_exit = job.get("expected_exit", 0),
            timeout_sec = job.get("timeout_sec", 5),
            expected_files = job.get("expected_files", []),
            depends_on =  job.get("depends_on", [])
        )
        job_configs.append(job_config)
    
    return job_configs