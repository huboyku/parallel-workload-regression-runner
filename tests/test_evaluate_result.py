import pytest

from src.runner import evaluate_result
from src.models import ExecutionResult, ExecutionStatus, JobStatus


def make_execution_result(**overrides ) -> ExecutionResult:

    data ={
        "name": "job1",
        "duration": 1.5,
        "returncode": 0,
        "expected_exit": 0,
        "missing_files": [],
        "status": ExecutionStatus.COMPLETED,
        "stdout": "ok",
        "stderr": "", 
    }
    data.update(overrides)
    return ExecutionResult(**data)

def test_evaluate_pass():
    result = make_execution_result()
    
    job_result = evaluate_result(result)
    
    assert job_result.status == JobStatus.PASS
    assert job_result.failure_reason is None 


def test_evaluate_result_timeout():
    result = make_execution_result(
        status = ExecutionStatus.TIMEOUT,
        returncode = -1,
    )
    
    job_result = evaluate_result(result)
    
    assert job_result.status == JobStatus.TIMEOUT
    assert job_result.failure_reason == "TIMEOUT"
    

def test_evaluate_result_unexpected_exception():
    result = make_execution_result(
        status = ExecutionStatus.ERROR,
        returncode = -1,
        stdout = ""
    )
    
    job_result = evaluate_result(result)
    
    assert job_result.status == JobStatus.ERROR
    assert job_result.failure_reason == "UNEXPECTED_EXCEPTION"
    
    
def test_evaluate_result_exit_code_mismatch():
    result = make_execution_result(
        returncode = 1,
        expected_exit = 0,
        )
    
    job_result = evaluate_result(result)
    
    assert job_result.status == JobStatus.FAIL
    assert job_result.failure_reason == "EXIT_CODE_MISMATCH"
    
    
def test_evaluate_result_missing_output():
    result = make_execution_result(
        missing_files = ["result.txt"])
    
    job_result = evaluate_result(result)
    
    assert job_result.status == JobStatus.FAIL
    assert job_result.failure_reason == "MISSING_OUTPUT"