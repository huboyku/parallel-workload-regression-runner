
import yaml
import subprocess 
import time
import argparse
from typing import Any 
from concurrent.futures import ProcessPoolExecutor
import os 
from datetime import datetime

def run_single_job(job_input: dict[str, Any]) -> dict[str, Any]:
    #return  {name:, status:, duration:, stdout:, stderr:, returncode:,}

    name = job_input["job"]["name"]
    command = job_input["job"]["command"]
    expected_exit = job_input["job"].get("expected_exit", 0)

    run_dir = os.path.join(job_input["base_run_dir"], name)
    os.makedirs(run_dir,exist_ok=True)

    execution_command = f"{command} --output-dir {run_dir}"

    start = time.time()
    
    result = subprocess.run(execution_command, capture_output=True, shell=True, text = True)

    end = time.time()
    duration = end - start
    
    stdout_path = os.path.join(run_dir,"stdout.log")
    stderr_path = os.path.join(run_dir,"stderr.log")
    
    with open(stdout_path,"w") as f:
        f.write(result.stdout)

    if result.stderr:
        with open(stderr_path,"w") as f:
            f.write(result.stderr)

    return {"name": name,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "expected_exit": expected_exit}

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--max-workers", type=int, default=2)
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    jobs = config["jobs"]

    summary = []
    
    start = time.time()

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_run_dir = os.path.join("runs",run_id)

    job_inputs = [{"job": job, "base_run_dir": base_run_dir} for job in jobs]

    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        results = list(executor.map(run_single_job, job_inputs))
    
    end = time.time()
    total_duration = end - start

    for result in results: 

        if result["returncode"] == result["expected_exit"]: 
            regression_status = "PASS"
        else:
            regression_status = "FAIL"

        summary.append({"name" : result["name"], "status" : regression_status, "duration" : result["duration"]})
    
    passed_tests = sum(1 for item in summary if item["status"] == "PASS")
    failed_tests = len(summary) - passed_tests
    
    print("Run finished")
    print(f"Total jobs: {len(summary)}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {failed_tests}")

    for res in summary:
        print(f"{res['name']} \u2192 {res['status']} ({res['duration']:.2f}s)")
    
    print(f"Total duration: {total_duration:.2f}")

if __name__ =="__main__":
    main()