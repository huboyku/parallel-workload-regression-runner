
import pytest
from src.models import JobConfig
from src.runner import validate_job_configs

def make_job_config(name: str, depends_on = None) -> JobConfig:
    
    return JobConfig(
        name = name,
        command = ["command", "run"],
        expected_exit = 0,
        timeout_sec = 5,
        expected_files = [],
        depends_on = depends_on or [],
    )
    

def test_validate_job_configs_duplicate_names():
    
    jobs = [make_job_config(name = "jobA"), make_job_config(name = "jobA")]
    
    with pytest.raises(ValueError, match = "Duplicate job names"):
        validate_job_configs(jobs)
    

def test_validate_job_configs_missing_dep():
    
    jobs = [make_job_config(name = "jobA", depends_on = ["jobB"])]
            
    with pytest.raises(ValueError, match = "has unknown dependency"):
        validate_job_configs(jobs)
        

def test_validate_job_configs_cycle():
    
    jobs = [make_job_config(name = "jobA", depends_on= ["jobB"]), make_job_config(name = "jobB", depends_on= ["jobA"])]
    
    with pytest.raises(ValueError, match = "Cycle detected at job"):
        validate_job_configs(jobs)