"""
unittests for listener
"""

from webapp.listener import Listener


class TestListener:
    """
    ensure the listener is behaving as expected
    """

    listener = Listener()

    async def test_compare_labels_match(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = ["foo", "bar"]
        resource_spec = ["a", "foo", "b", "bar", "c"]
        assert (
            await self.listener.compare_labels(job_spec, resource_spec)
            is True
        )

    async def test_compare_labels_nomatch(self):
        """
        ensure we get an expected result with valid data but no match
        """
        job_spec = ["foo", "zar"]
        resource_spec = ["a", "foo", "b", "bar", "c"]
        assert (
            await self.listener.compare_labels(job_spec, resource_spec)
            is False
        )

    async def test_compare_gpus_match(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = [{"brand": "amd", "model": "hd8490"}]
        resource_spec = [{"brand": "amd", "model": "hd8490", "memory": 4}]
        assert (
            await self.listener.compare_gpus(job_spec, resource_spec) is True
        )

    async def test_compare_gpus_nomatch(self):
        """
        ensure we get an expected result with valid data but no match
        """
        job_spec = [{"brand": "nvidia", "model": "rtx4000"}]
        resource_spec = [{"brand": "amd", "model": "hd8490", "memory": 4}]
        assert (
            await self.listener.compare_gpus(job_spec, resource_spec) is False
        )

    async def test_compare_gpus_match_multiple(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = [
            {"brand": "amd", "model": "hd8490"},
            {"brand": "nvidia", "model": "rtx4000"},
        ]
        resource_spec = [
            {"brand": "amd", "model": "hd8490", "memory": 4},
            {"brand": "nvidia", "model": "rtx4000"},
            {"brand": "nvidia", "model": "rtx5000"},
        ]
        assert (
            await self.listener.compare_gpus(job_spec, resource_spec) is True
        )

    async def test_compare_cpuormem_match(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = 8
        resource_spec = 8
        assert (
            await self.listener.compare_cpuormem(job_spec, resource_spec)
            is True
        )

    async def test_compare_cpuormem_nomatch(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = 8
        resource_spec = 16
        assert (
            await self.listener.compare_cpuormem(job_spec, resource_spec)
            is False
        )

    async def test_compare_cpuormem_gte_match(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = ">=8"
        resource_spec = 16
        assert (
            await self.listener.compare_cpuormem(job_spec, resource_spec)
            is True
        )

    async def test_compare_cpuormem_gte_nomatch(self):
        """
        ensure we get an expected result with valid data
        """
        job_spec = ">=8"
        resource_spec = 4
        assert (
            await self.listener.compare_cpuormem(job_spec, resource_spec)
            is False
        )
