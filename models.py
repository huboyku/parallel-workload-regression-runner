from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict

class RunCounts(TypedDict):
    passed : int
    failed : int 
    timeout : int
    error : int

class JobStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"

class ExecutionStatus(Enum):
    COMPLETED = "COMPLETED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"

@dataclass
class JobConfig:
    name : str 
    command : list[str]
    expected_exit : int = 0 
    timeout_sec : int = 5
    expected_files : list[str] = field(default_factory=list)
    depends_on : list[str] = field(default_factory=list)

@dataclass
class ExecutionResult:
    name : str
    duration : float
    returncode : int
    expected_exit : int
    status : ExecutionStatus
    stdout: str
    stderr: str   
    missing_files : list[str] = field(default_factory=list)

@dataclass
class JobRunRequest:
    job : JobConfig
    base_run_dir : str

@dataclass
class JobResult:
    name : str
    status : JobStatus
    duration : float 
    returncode : int
    failure_reason : str | None
    missing_files : list[str] = field(default_factory=list)

