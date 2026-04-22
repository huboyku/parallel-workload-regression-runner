# Parallel Workload Runner

A dependency-aware parallel workload runner designed to simulate regression systems commonly used in EDA (Electronic Design Automation) and large-scale software testing workflows.

This tool executes jobs with dependency constraints, captures execution results, and produces structured summaries for analysis.


## 🚀 Features
- Dependency-aware scheduling
- Parallel execution using ProcessPoolExecutor
- Failure handling & skip logic
- Timeout support
- Output validation
- Structured result evaluation (PASS / FAIL / ERROR / TIMEOUT / SKIPPED)
- Run artifacts (logs + summary.json)


## 🧠 System Overview

Scheduler    
- Tracks pending, running, completed jobs
- Enforces dependency constraints
- Submits ready jobs

Execution Engine
- Runs jobs via subprocess
- Captures stdout, stderr, return code, duration
- Handles timeout and errors

Result Evaluation
- Maps execution results to regression status
- Validates exit codes and expected outputs


## 📁 Project Structure

```
.
├── main.py
├── models.py
├── config_loader.py
├── runs/
│   └── <run_id>/
│       ├── job1/
│       │   ├── stdout.log
│       │   └── stderr.log
│       └── summary.json
└── configs/
    └── sample.yaml
```

## ⚙️ Job Configuration (YAML)

```
jobs:
  - name: job_a
    command: ["python", "worker_sleep.py", "1"]
    expected_exit: 0
    timeout_sec: 5
    expected_files: []
    depends_on: []

  - name: job_b
    command: ["python", "worker_sleep.py", "2"]
    depends_on: ["job_a"]

  - name: job_c
    command: ["python", "worker_sleep.py", "3"]
    depends_on: ["job_a"]
```

## ▶️ How to Run

python main.py configs/sample.yaml --max-workers 2


## 📊 Example Output

- Run finished
- Total duration: 5.23s
- Total jobs: 3
- Passed tests: 2
- Failed tests: 1
- Error tests: 0
- Timed out tests: 0
- Skipped tests: 0

Summary is written to:

runs/<run_id>/summary.json


## 🧪 Validation Checks
- Duplicate job names
- Missing dependencies
- Cyclic dependencies (DFS-based detection)

## 📌 Current Limitations
- Uses requested resource simulation only
- Supports subprocess-based jobs only
- No retry mechanism yet
- No resource-aware scheduling yet

## 🔮 Future Improvements
- Resource-aware scheduling
- Retry mechanism
- Structured logging
- DAG visualization
- Run comparison

## 🛠️ Tech Stack
- Python
- concurrent.futures
- subprocess
- YAML

