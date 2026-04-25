"""Resource usage data model."""

from pydantic import BaseModel


class ResourceUsage(BaseModel):
    """Holds resource statistics (VRAM, RAM, CPU, GPU)."""

    vram_used: float = 0.0
    vram_total: float = 0.0
    ram_used: float = 0.0
    ram_total: float = 0.0
    cpu_usage: float = 0.0
    gpu_count: int = 0

    @property
    def vram_percent(self) -> float:
        if self.vram_total == 0:
            return 0.0
        return (self.vram_used / self.vram_total) * 100.0

    @property
    def ram_percent(self) -> float:
        if self.ram_total == 0:
            return 0.0
        return (self.ram_used / self.ram_total) * 100.0


class GPUStats(BaseModel):
    """Per-GPU statistics."""

    gpu_id: int
    vram_used: float = 0.0
    vram_total: float = 0.0
    temperature: float = 0.0
    utilization: float = 0.0
