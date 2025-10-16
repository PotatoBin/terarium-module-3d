"""Utility for allocating GPU devices across jobs."""
from __future__ import annotations

import os
import subprocess
from collections import deque
from contextlib import contextmanager
from threading import Condition
from typing import Deque, Iterable, Iterator, List, Optional


def query_available_gpus() -> List[str]:
    """Detect GPU indices from the environment or the system."""
    env = os.environ.get("CUDA_VISIBLE_DEVICES") or os.environ.get("NVIDIA_VISIBLE_DEVICES")
    if env:
        return [gpu.strip() for gpu in env.split(",") if gpu.strip()]

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):  # pragma: no cover - GPU absent
        return []

    gpus = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return gpus


class GpuPool:
    """Simple thread-safe GPU allocator supporting blocking acquire/release."""

    def __init__(self, gpu_ids: Optional[Iterable[str]] = None, max_slots: Optional[int] = None):
        if gpu_ids is None:
            gpu_ids = query_available_gpus()
        gpu_list = list(gpu_ids)
        if not gpu_list:
            gpu_list = ["cpu"]
        self._available: Deque[str] = deque(gpu_list)
        self._condition = Condition()
        self._max_slots = max_slots or len(gpu_list)

    @contextmanager
    def reserve(self) -> Iterator[str]:
        """Reserve a GPU id for the duration of the context manager."""
        gpu_id = self.acquire()
        try:
            yield gpu_id
        finally:
            self.release(gpu_id)

    def acquire(self) -> str:
        with self._condition:
            while not self._available:
                self._condition.wait()
            gpu_id = self._available.popleft()
            return gpu_id

    def release(self, gpu_id: str) -> None:
        with self._condition:
            if len(self._available) >= self._max_slots:
                return
            self._available.append(gpu_id)
            self._condition.notify()

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"GpuPool(available={list(self._available)})"


__all__ = ["GpuPool", "query_available_gpus"]
