"""Tests for resource usage model."""

import pytest
from llm_control.models.resource import ResourceUsage, GPUStats


class TestResourceUsage:
    def test_create_defaults(self):
        usage = ResourceUsage()
        assert usage.vram_used == 0.0
        assert usage.vram_total == 0.0
        assert usage.ram_used == 0.0
        assert usage.ram_total == 0.0
        assert usage.cpu_usage == 0.0
        assert usage.gpu_count == 0

    def test_create_with_values(self):
        usage = ResourceUsage(
            vram_used=4.5, vram_total=8.0, ram_used=12.0, ram_total=32.0,
            cpu_usage=45.5, gpu_count=2
        )
        assert usage.vram_used == 4.5

    def test_vram_percent(self):
        usage = ResourceUsage(vram_used=4.0, vram_total=8.0)
        assert usage.vram_percent == 50.0

    def test_vram_percent_zero_total(self):
        usage = ResourceUsage(vram_used=0.0, vram_total=0.0)
        assert usage.vram_percent == 0.0

    def test_ram_percent(self):
        usage = ResourceUsage(ram_used=16.0, ram_total=32.0)
        assert usage.ram_percent == 50.0

    def test_ram_percent_zero_total(self):
        usage = ResourceUsage(ram_used=0.0, ram_total=0.0)
        assert usage.ram_percent == 0.0


class TestGPUStats:
    def test_create_gpu_stats(self):
        stats = GPUStats(gpu_id=0, vram_used=4.5, temperature=65.0)
        assert stats.gpu_id == 0
        assert stats.temperature == 65.0
