import os
from dataclasses import dataclass

from .matrix import MatrixError


@dataclass(frozen=True)
class ResourceBudget:
    vcpus: int
    memory_mib: int

    def validate(self) -> None:
        if (
            isinstance(self.vcpus, bool)
            or not isinstance(self.vcpus, int)
            or isinstance(self.memory_mib, bool)
            or not isinstance(self.memory_mib, int)
            or self.vcpus < 1
            or self.memory_mib < 512
        ):
            raise MatrixError("Resource budgets must provide at least 1 vCPU and 512 MiB of memory.")


@dataclass(frozen=True)
class BuildJob:
    job_id: str
    variant_name: str
    target: str
    vcpus: int
    memory_mib: int

    def validate(self) -> None:
        if not self.job_id.strip() or not self.variant_name.strip() or not self.target.strip():
            raise MatrixError("Build jobs require an ID, variant, and target.")
        if (
            isinstance(self.vcpus, bool)
            or not isinstance(self.vcpus, int)
            or isinstance(self.memory_mib, bool)
            or not isinstance(self.memory_mib, int)
            or self.vcpus < 1
            or self.memory_mib < 512
        ):
            raise MatrixError("Each build must request at least 1 vCPU and 512 MiB of memory.")


def suggested_resource_budget() -> ResourceBudget:
    vcpus = max(1, (os.cpu_count() or 2) - 2)
    try:
        total_mib = (
            os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
        ) // (1024 * 1024)
    except (OSError, ValueError):
        total_mib = 8192
    memory_mib = max(512, int(total_mib * 0.75) - 4096)
    return ResourceBudget(vcpus, memory_mib)


def select_startable_jobs(
    pending: list[BuildJob],
    running: list[BuildJob],
    budget: ResourceBudget,
) -> list[BuildJob]:
    budget.validate()
    seen: set[str] = set()
    for job in [*running, *pending]:
        job.validate()
        if job.job_id in seen:
            raise MatrixError(f"Duplicate build job ID '{job.job_id}'.")
        seen.add(job.job_id)

    used_vcpus = sum(job.vcpus for job in running)
    used_memory = sum(job.memory_mib for job in running)
    available_vcpus = max(0, budget.vcpus - used_vcpus)
    available_memory = max(0, budget.memory_mib - used_memory)
    selected: list[BuildJob] = []
    for job in pending:
        if job.vcpus <= available_vcpus and job.memory_mib <= available_memory:
            selected.append(job)
            available_vcpus -= job.vcpus
            available_memory -= job.memory_mib
    return selected
