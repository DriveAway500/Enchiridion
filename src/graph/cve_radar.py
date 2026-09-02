"""
Optimized CVSS radar chart generator for high throughput (e.g. a Discord bot).

Usage:

    gen = CVSSRadarChartGenerator()
    cve_id, png_bytes = await gen.generate_chart(json_data)
    # ...
    results = await gen.generate_batch(list_of_json_items)
    # ...
    gen.close()  # when shutting down the application
"""

import io
import json
import asyncio
import numpy as np
from concurrent.futures import ProcessPoolExecutor

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

# ---------------------------------------------------------------------------
# Shared constants (also used inside the worker processes)
# ---------------------------------------------------------------------------

MAPPINGS = {
    "attackVector": {"NETWORK": 10.0, "ADJACENT_NETWORK": 7.5, "LOCAL": 5.0, "PHYSICAL": 2.5},
    "attackComplexity": {"LOW": 10.0, "HIGH": 4.0},
    "privilegesRequired": {"NONE": 10.0, "LOW": 5.0, "HIGH": 2.5},
    "userInteraction": {"NONE": 10.0, "REQUIRED": 4.0, "PASSIVE": 4.0, "ACTIVE": 8.0},
    "confidentialityImpact": {"HIGH": 10.0, "LOW": 5.0, "NONE": 0.0},
    "integrityImpact": {"HIGH": 10.0, "LOW": 5.0, "NONE": 0.0},
    "availabilityImpact": {"HIGH": 10.0, "LOW": 5.0, "NONE": 0.0},
}

CATEGORIES = [
    "Attack Vector\n(AV)",
    "Complexity\n(AC)",
    "Privileges\n(PR)",
    "User Interaction\n(UI)",
    "Confidentiality\n(C)",
    "Integrity\n(I)",
    "Availability\n(A)",
]

_NUM_VARS = len(CATEGORIES)
_ANGLES = np.linspace(0, 2 * np.pi, _NUM_VARS, endpoint=False).tolist()
_ANGLES = _ANGLES + _ANGLES[:1]

# ---------------------------------------------------------------------------
# Per-worker-process state — each process in the pool has its own copy,
# created once in _init_worker and reused for every subsequent call made
# to that process.
# ---------------------------------------------------------------------------

_worker_state = {}


def _init_worker(figsize, dpi, color, alpha):
    """Runs once per worker process when the pool is created."""
    fig = Figure(figsize=figsize, dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111, polar=True)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(_ANGLES[:-1])
    ax.set_xticklabels(CATEGORIES, size=10)
    ax.set_rlabel_position(0)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], color="grey", size=8)
    ax.set_ylim(0, 10)

    # Fixed margins computed once (replaces bbox_inches='tight')
    fig.subplots_adjust(left=0.08, right=0.92, top=0.85, bottom=0.08)

    zeros = [0.0] * len(_ANGLES)
    (line,) = ax.plot(_ANGLES, zeros, color=color, linewidth=2, linestyle="solid")
    fill_patch = ax.fill(_ANGLES, zeros, color=color, alpha=alpha)[0]
    title = ax.set_title("", size=14, pad=20, fontweight="bold")

    _worker_state.update(
        fig=fig,
        canvas=canvas,
        ax=ax,
        line=line,
        fill_patch=fill_patch,
        title=title,
        dpi=dpi,
    )


def _get_values(cvss):
    vals = [
        MAPPINGS["attackVector"].get(cvss.get("attackVector"), 0.0),
        MAPPINGS["attackComplexity"].get(cvss.get("attackComplexity"), 0.0),
        MAPPINGS["privilegesRequired"].get(cvss.get("privilegesRequired"), 0.0),
        MAPPINGS["userInteraction"].get(cvss.get("userInteraction"), 0.0),
        MAPPINGS["confidentialityImpact"].get(cvss.get("confidentialityImpact"), 0.0),
        MAPPINGS["integrityImpact"].get(cvss.get("integrityImpact"), 0.0),
        MAPPINGS["availabilityImpact"].get(cvss.get("availabilityImpact"), 0.0),
    ]
    return vals + vals[:1]


def _render_chart_worker(cve_id, cvss):
    """Runs inside the worker process. Reuses the existing figure, only
    updating the artists that change (line, fill, title)."""
    state = _worker_state
    values = _get_values(cvss)

    state["line"].set_data(_ANGLES, values)
    state["fill_patch"].set_xy(np.column_stack([_ANGLES, values]))
    state["title"].set_text(f"CVSS Metrics — {cve_id}")

    buffer = io.BytesIO()
    state["fig"].savefig(buffer, format="png", dpi=state["dpi"])
    buffer.seek(0)
    return cve_id, buffer.getvalue()


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class CVSSRadarChartGenerator:
    def __init__(self, figsize=(6, 6), dpi=100, color="#d9534f", alpha=0.3, max_workers=None):
        self.figsize = figsize
        self.dpi = dpi
        self.color = color
        self.alpha = alpha
        self._executor = ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=_init_worker,
            initargs=(figsize, dpi, color, alpha),
        )

    @staticmethod
    def _extract_cvss_data(item):
        if isinstance(item, str):
            item = json.loads(item)

        cve_node = item.get("cve", item)
        cve_id = cve_node.get("id", "CVE-UNKNOWN")
        metrics = cve_node.get("metrics", {})

        cvss_data = None
        if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
            cvss_data = metrics["cvssMetricV31"][0].get("cvssData")
        elif "cvssMetricV40" in metrics and metrics["cvssMetricV40"]:
            cvss_data = metrics["cvssMetricV40"][0].get("cvssData")

        if not cvss_data:
            raise ValueError(f"CVSS metrics not found in record {cve_id}")

        return cve_id, cvss_data

    async def generate_chart(self, json_data) -> tuple[str, bytes]:
        cve_id, cvss = self._extract_cvss_data(json_data)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, _render_chart_worker, cve_id, cvss)

    async def generate_batch(self, json_list) -> list[tuple[str, bytes]]:
        loop = asyncio.get_running_loop()
        futures = []

        for item in json_list:
            try:
                cve_id, cvss = self._extract_cvss_data(item)
            except Exception as e:
                print(f"Error extracting item: {e}")
                continue
            futures.append(loop.run_in_executor(self._executor, _render_chart_worker, cve_id, cvss))

        results = await asyncio.gather(*futures, return_exceptions=True)

        output = []
        for res in results:
            if isinstance(res, Exception):
                print(f"Error processing item: {res}")
            else:
                output.append(res)
        return output

    def close(self):
        """Call this when shutting down the application to tear down the worker processes."""
        self._executor.shutdown(wait=True)