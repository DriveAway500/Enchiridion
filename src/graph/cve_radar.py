import json
import asyncio
from pathlib import Path
from typing import Union, List, Tuple
from chart_lib import CVSSRadarChartGenerator


class CVSSRadarService:
    """Async service layer to handle CVSS JSON payloads and generate radar chart PNGs

    via the underlying high-performance Rust library.
    """

    def __init__(self, width: i32 = 600, height: i32 = 600) -> None:
        """Initialize the chart generator with dimensions."""
        self.width = width
        self.height = height
        self._generator = CVSSRadarChartGenerator(width=width, height=height)

    @staticmethod
    def _normalize_json_payload(payload: Union[str, dict]) -> str:
        """Ensure input payload is converted to a valid JSON string."""
        if isinstance(payload, dict):
            return json.dumps(payload)
        elif isinstance(payload, str):
            return payload
        else:
            raise TypeError(
                f"Unsupported JSON type: {type(payload)}. Expected dict or str."
            )

    async def generate_single(
        self, json_data: Union[str, dict]
    ) -> Tuple[str, bytes]:
        """Process a single JSON record asynchronously.

        Returns a tuple of (cve_id, png_bytes).
        """
        raw_json = self._normalize_json_payload(json_data)
        return await self._generator.generate_chart(raw_json)

    async def generate_batch(
        self, json_list: List[Union[str, dict]]
    ) -> List[Tuple[str, bytes]]:
        """Process a batch of JSON records concurrently in Rust.

        Returns a list of tuples: [(cve_id, png_bytes), ...]
        """
        raw_jsons = [self._normalize_json_payload(item) for item in json_list]
        return await self._generator.generate_batch(raw_jsons)

    async def process_file(
        self, file_path: Union[str, Path]
    ) -> Tuple[str, bytes]:
        """Read a JSON file asynchronously and generate its radar chart PNG."""
        path = Path(file_path)
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return await self.generate_single(content)

    async def process_file_batch(
        self, file_paths: List[Union[str, Path]]
    ) -> List[Tuple[str, bytes]]:
        """Read multiple JSON files asynchronously and generate their PNGs in parallel."""

        async def _read_file(p: Union[str, Path]) -> str:
            return await asyncio.to_thread(
                Path(p).read_text, encoding="utf-8"
            )

        raw_jsons = await asyncio.gather(
            *[_read_file(fp) for fp in file_paths]
        )
        return await self._generator.generate_batch(raw_jsons)