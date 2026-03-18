
import yaml
import subprocess 
import time
import argparse
from typing import Any 
from concurrent.futures import ProcessPoolExecutor
import os 
from datetime import datetime
import json 

def run_single_job(job_input: dict[str, Any]) -> dict[str, Any]:
    #return  {name:, status:, duration:, stdout:, stderr:, returncode:,}

    name = job_input["job"]["name"]
    command = job_input["job"]["command"]
    expected_exit = job_input["job"].get("expected_exit", 0)
    timeout = job_input["job"].get("timeout_sec", 5)
    expected_files = job_input["job"].get("expected_files", [])

    run_dir = os.path.join(job_input["base_run_dir"], name)
    os.makedirs(run_dir,exist_ok=True)

    execution_command = f"{command} --output-dir {run_dir}"

    start = time.perf_counter()
    
    try:
        result = subprocess.run(execution_command, capture_output=True, shell=True, text = True, timeout = timeout)
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
        status = "COMPLETED"

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        returncode = -1
        status = "TIMEOUT"
    
    except Exception as e:
        stdout = ""
        stderr = str(e)
        returncode = -1 
        status = "ERROR"
    
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

    return {"name": name,
            "duration": duration,
            "returncode": returncode,
            "expected_exit": expected_exit,
            "missing_files": missing_files,
            "status": status}

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--max-workers", type=int, default=2)
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    jobs = config["jobs"]

    summary = []
    
    start = time.perf_counter()

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_run_dir = os.path.join("runs",run_id)
    os.makedirs(base_run_dir, exist_ok=True)

    job_inputs = [{"job": job, "base_run_dir": base_run_dir} for job in jobs]

    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        results = list(executor.map(run_single_job, job_inputs))
    
    end = time.perf_counter()
    total_duration = end - start

    for result in results: 

        if result["status"] == "TIMEOUT":
            regression_status = "TIMEOUT"
            failure_reason = "TIMEOUT"
        elif result["status"] == "ERROR":
            regression_status = "ERROR"
            failure_reason = "UNEXPECTED_EXCEPTION"
        elif result["returncode"] != result["expected_exit"]:
            regression_status = "FAIL"
            failure_reason = "EXIT_CODE_MISMATCH"
        elif result["missing_files"]:
            regression_status = "FAIL"
            failure_reason = "MISSING_OUTPUT"
        else:
            regression_status = "PASS"
            failure_reason = None

        summary.append({
            "name": result["name"],
            "status": regression_status,
            "duration": result["duration"],
            "returncode": result["returncode"],
            "failure_reason": failure_reason,
            "missing_files": result["missing_files"],
        })
        
    passed_tests = sum(1 for item in summary if item["status"] == "PASS")
    failed_tests = sum(1 for item in summary if item["status"] == "FAIL")
    timeout_tests = sum(1 for item in summary if item["status"] == "TIMEOUT")
    error_tests = sum(1 for item in summary if item["status"] == "ERROR")

    print("Run finished")
    print(f"Total jobs: {len(summary)}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {failed_tests}")
    print(f"Error tests: {error_tests}")
    print(f"Timed out tests: {timeout_tests}")

    for res in summary:
        if res["failure_reason"]:
            print(f"{res['name']} → {res['status']} ({res['failure_reason']}) ({res['duration']:.2f}s)")
        else:
            print(f"{res['name']} → {res['status']} ({res['duration']:.2f}s)")
            
    print(f"Total duration: {total_duration:.2f}s")

    summary_data = {
        "run_id": run_id,
        "total_duration": total_duration,
        "total_jobs": len(summary),
        "passed": passed_tests,
        "failed": failed_tests,
        "errors": error_tests,
        "timeout": timeout_tests,
        "jobs": summary
    }

    summary_path = os.path.join(base_run_dir,"summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Summary written to: {summary_path}")

if __name__ =="__main__":
    main()