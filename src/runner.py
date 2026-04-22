import yaml
import subprocess 
import time
import argparse
from typing import Dict
from concurrent.futures import ProcessPoolExecutor, as_completed
import os 
from datetime import datetime
import json 
from .config_loader import load_jobs_from_yaml
from .models import ExecutionResult, JobRunRequest, JobResult, JobStatus, ExecutionStatus, RunCounts, JobConfig
from dataclasses import asdict

def run_single_job(job_input: JobRunRequest) -> ExecutionResult:
    #return  {name:, status:, duration:, stdout:, stderr:, returncode:,}
    job = job_input.job
    name = job.name
    command = job.command
    expected_exit = job.expected_exit
    timeout = job.timeout_sec
    expected_files = job.expected_files

    run_dir = os.path.join(job_input.base_run_dir, name)
    os.makedirs(run_dir,exist_ok=True)

    execution_command = command + ["--output-dir", run_dir]

    start = time.perf_counter()
    
    try:
        result = subprocess.run(execution_command, capture_output=True, shell=False, text = True, timeout = timeout)
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
        status = ExecutionStatus.COMPLETED

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        returncode = -1
        status = ExecutionStatus.TIMEOUT
    
    except Exception as e:
        stdout = ""
        stderr = str(e)
        returncode = -1 
        status = ExecutionStatus.ERROR
    
    end = time.perf_counter()
    duration = end - start
    
    stdout_path = os.path.join(run_dir,"stdout.log")
    stderr_path = os.path.join(run_dir,"stderr.log")

    missing_files = []
    for filename in expected_files:
        fullpath = os.path.join(run_dir, filename)
        if not os.path.exists(fullpath):
            missing_files.append(filename)

    with open(stdout_path,"w") as f:
        f.write(stdout)

    with open(stderr_path,"w") as f:
        f.write(stderr)

    return ExecutionResult (
        name = name,
        duration = duration,
        returncode = returncode,
        expected_exit = expected_exit,
        missing_files = missing_files,
        status = status,
        stdout = stdout,
        stderr = stderr)

def run_scheduler(job_configs: list[JobConfig], max_workers: int , base_run_dir: str) -> Dict[str, JobResult]:

    pending_jobs = {job.name : job for job in job_configs}
    running_futures = {}
    completed_job_results = {}

    with ProcessPoolExecutor(max_workers=max_workers) as executor:

        while pending_jobs or running_futures:

            for job_name, job in list(pending_jobs.items()):

                dependencies = job.depends_on or []

                # Case 1: no dependencies -> ready
                if not dependencies:
                    #job is ready
                    job_input = JobRunRequest(job =job, base_run_dir = base_run_dir)
                    future  = executor.submit(run_single_job, job_input)
                    running_futures[future] = job_name
                    pending_jobs.pop(job_name)
                    continue
                
                # Case 2: has dependencies -> check their status
                all_passed = True
                any_failed = False

                for dep in dependencies:
                    # Has not finished yet
                    if dep not in completed_job_results:
                        all_passed = False
                        break
                    
                    # Finished but did not passed
                    if completed_job_results[dep].status != JobStatus.PASS: 
                        all_passed = False
                        any_failed = True 
                        break
                
                if all_passed:
                    # ready
                    job_input = JobRunRequest(job = job, base_run_dir = base_run_dir)
                    future = executor.submit(run_single_job, job_input)
                    running_futures[future] = job_name
                    pending_jobs.pop(job_name)

                elif any_failed:
                    # skipped
                    completed_job_results[job_name] = JobResult(
                        name=job_name,
                        status=JobStatus.SKIPPED,
                        duration=0.0,
                        returncode=None,
                        failure_reason="Dependency failed",
                        missing_files=[],
                    )
                    pending_jobs.pop(job_name)
                    
                else:
                    #blocked
                    pass

            if running_futures:
                done_future = next(as_completed(running_futures))
                job_name = running_futures.pop(done_future)

                result = done_future.result()
                job_result = evaluate_result(result)

                completed_job_results[job_name] = job_result

    return completed_job_results

def validate_job_configs(job_configs: list[JobConfig]) -> None:
    job_names = [job.name for job in job_configs]
    #check duplicates, error for which is duplicated, check missing dep, check cyclic
    seen = set()
    duplicates = set()

    for name in job_names:
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)
    if duplicates:
        raise ValueError(f"Duplicate job names: {duplicates}")

    set_job_names = set(job_names)
    missing_dep = []

    for job in job_configs:
        dependencies = job.depends_on or []

        for dep in dependencies:

            if dep not in set_job_names:
                missing_dep.append((job.name,dep))

    if missing_dep:
        error_msg = "\n".join(f"Job '{job}' has unknown dependency '{dep}'" for job, dep in missing_dep)
        raise ValueError(error_msg)

    graph = {}

    for job in job_configs:
        dependencies = job.depends_on or []
        graph[job.name] = dependencies

    visiting = set()
    visited = set()

    def dfs(node):
        if node in visiting: 
            raise ValueError(f"Cycle detected at job '{node}'")

        if node in visited:
            return

        visiting.add(node)

        for dep in graph[node]:
            dfs(dep)
        
        visiting.remove(node)
        visited.add(node)
        
    for node in graph:
        if node not in visited: 
            dfs(node)

def evaluate_result(result:ExecutionResult) -> JobResult:

    if result.status == ExecutionStatus.TIMEOUT:
        regression_status = JobStatus.TIMEOUT
        failure_reason = "TIMEOUT"
    elif result.status == ExecutionStatus.ERROR:
        regression_status = JobStatus.ERROR
        failure_reason = "UNEXPECTED_EXCEPTION"
    elif result.returncode != result.expected_exit:
        regression_status = JobStatus.FAIL
        failure_reason = "EXIT_CODE_MISMATCH"
    elif result.missing_files:
        regression_status = JobStatus.FAIL
        failure_reason = "MISSING_OUTPUT"
    else:
        regression_status = JobStatus.PASS
        failure_reason = None

    return JobResult(
        name = result.name,
        status = regression_status,
        duration = result.duration,
        returncode = result.returncode,
        failure_reason = failure_reason,
        missing_files = result.missing_files,
    )

def calculate_run_counts(job_results: list[JobResult]) -> RunCounts:
    run_counts = RunCounts(
        passed=sum(1 for item in job_results if item.status == JobStatus.PASS),
        failed=sum(1 for item in job_results if item.status == JobStatus.FAIL),
        timeout=sum(1 for item in job_results if item.status == JobStatus.TIMEOUT),
        error=sum(1 for item in job_results if item.status == JobStatus.ERROR),
        skipped=sum(1 for item in job_results if item.status == JobStatus.SKIPPED),
    )
    return run_counts

def print_regression_summary(job_results, total_duration, run_counts):

    print("Run finished")
    print(f"Total duration: {total_duration:.2f}s")
    print(f"Total jobs: {len(job_results)}")
    print(f"Passed tests: {run_counts['passed']}")
    print(f"Failed tests: {run_counts['failed']}")
    print(f"Error tests: {run_counts['error']}")
    print(f"Timed out tests: {run_counts['timeout']}")
    print(f"Skipped tests: {run_counts['skipped']}")

    for res in job_results:
        if res.failure_reason:
            print(f"{res.name} → {res.status.value} ({res.failure_reason}) ({res.duration:.2f}s)")
        else:
            print(f"{res.name} → {res.status.value} ({res.duration:.2f}s)")

def build_run_summary_data(run_id, total_duration, job_results, run_counts) -> dict:   
    
    return {
        "run_id": run_id,
        "total_duration": total_duration,
        "total_jobs": len(job_results),
        "passed": run_counts['passed'],
        "failed": run_counts['failed'],
        "errors": run_counts['error'],
        "timeout": run_counts['timeout'],
        "skipped": run_counts['skipped'],
        "jobs": [
            {
                **asdict(job_result),
                "status": job_result.status.value
            }
            for job_result in job_results
        ]
    }

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--max-workers", type=int, default=2)
    args = parser.parse_args()

    job_configs = load_jobs_from_yaml(args.config)

    start = time.perf_counter()

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_run_dir = os.path.join("runs",run_id)
    os.makedirs(base_run_dir, exist_ok=True)

    validate_job_configs(job_configs)

    completed_job_results =run_scheduler(
        job_configs=job_configs,
        max_workers=args.max_workers,
        base_run_dir=base_run_dir,
    )

    end = time.perf_counter()
    total_duration = end - start

    regression_results = list(completed_job_results.values())
    
    run_counts = calculate_run_counts(regression_results)

    print_regression_summary(regression_results, total_duration, run_counts)

    run_summary_data = build_run_summary_data(run_id, total_duration, regression_results, run_counts)
    
    summary_path = os.path.join(base_run_dir,"summary.json")
    with open(summary_path, "w") as f:
        json.dump(run_summary_data, f, indent=2)

    print(f"Summary written to: {summary_path}")

if __name__ =="__main__":
    main()