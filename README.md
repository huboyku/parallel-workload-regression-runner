# Parallel Workload Regression Runner

A lightweight Python-based workload runner that reads jobs from a YAML configuration file, executes them in parallel, captures per-job logs, and validates regression outcomes.

## Features

- YAML-based job configuration
- Parallel job execution
- Configurable worker count
- Per-job run directories
- stdout and stderr logging
- Regression validation using expected exit codes

## Project structure

parallel-runner/
runner.py
config.yaml
workloads/
sleep_job.py
fail_job.py
runs/

## Example config

jobs:
  - name: sleep1
    command: python3 workloads/sleep_job.py
    expected_exit: 0

  - name: fail1
    command: python3 workloads/fail_job.py
    expected_exit: 1

## Usage

Run with default workers:

python3 runner.py config.yaml

Run with custom workers:

python3 runner.py config.yaml --max-workers 2

## Example output

Run finished  
Total jobs: 4  
Passed tests: 4  
Failed tests: 0  

sleep1 → PASS (5.09s)  
sleep2 → PASS (5.07s)  
sleep3 → PASS (5.09s)  
fail1 → PASS (0.04s)  

Total duration: 5.13

## Notes

A job passes when its actual exit code matches the expected exit code defined in the YAML configuration.
