import io
import json
import asyncio
import numpy as np
import matplotlib.pyplot as plt

class CVSSRadarChartGenerator:

    MAPPINGS = {
        "attackVector": {"NETWORK": 10.0, "ADJACENT_NETWORK": 7.5, "LOCAL": 5.0, "PHYSICAL": 2.5},
        "attackComplexity": {"LOW": 10.0, "HIGH": 4.0},
        "privilegesRequired": {"NONE": 10.0, "LOW": 5.0, "HIGH": 2.5},
        "userInteraction": {"NONE": 10.0, "REQUIRED": 4.0, "PASSIVE": 4.0, "ACTIVE": 8.0},
        "confidentialityImpact": {"HIGH": 10.0, "LOW": 5.0, "NONE": 0.0},
        "integrityImpact": {"HIGH": 10.0, "LOW": 5.0, "NONE": 0.0},
        "availabilityImpact": {"HIGH": 10.0, "LOW": 5.0, "NONE": 0.0}
    }

    CATEGORIES = [
        "Attack Vector\n(AV)",
        "Complexity\n(AC)",
        "Privileges\n(PR)",
        "User Interaction\n(UI)",
        "Confidentiality\n(C)",
        "Integrity\n(I)",
        "Availability\n(A)"
    ]

    def __init__(self, figsize=(7, 7), dpi=100, color='#d9534f', alpha=0.3):
        self.figsize = figsize
        self.dpi = dpi
        self.color = color
        self.alpha = alpha

        num_vars = len(self.CATEGORIES)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        self.angles = angles + angles[:1]

    def _extract_cvss_data(self, item):
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

    def _get_values(self, cvss):
        vals = [
            self.MAPPINGS["attackVector"].get(cvss.get("attackVector"), 0.0),
            self.MAPPINGS["attackComplexity"].get(cvss.get("attackComplexity"), 0.0),
            self.MAPPINGS["privilegesRequired"].get(cvss.get("privilegesRequired"), 0.0),
            self.MAPPINGS["userInteraction"].get(cvss.get("userInteraction"), 0.0),
            self.MAPPINGS["confidentialityImpact"].get(cvss.get("confidentialityImpact"), 0.0),
            self.MAPPINGS["integrityImpact"].get(cvss.get("integrityImpact"), 0.0),
            self.MAPPINGS["availabilityImpact"].get(cvss.get("availabilityImpact"), 0.0),
        ]
        return vals + vals[:1]

    def _generate_chart_sync(self, json_data) -> tuple[str, bytes]:
        cve_id, cvss = self._extract_cvss_data(json_data)
        values = self._get_values(cvss)

        fig, ax = plt.subplots(figsize=self.figsize, subplot_kw=dict(polar=True))

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        ax.plot(self.angles, values, color=self.color, linewidth=2, linestyle='solid')
        ax.fill(self.angles, values, color=self.color, alpha=self.alpha)

        ax.set_xticks(self.angles[:-1])
        ax.set_xticklabels(self.CATEGORIES, size=10)
        ax.set_rlabel_position(0)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_yticklabels(["2", "4", "6", "8", "10"], color="grey", size=8)
        ax.set_ylim(0, 10)
        ax.set_title(f"CVSS Metrics — {cve_id}", size=14, pad=20, fontweight='bold')

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)

        return cve_id, buffer.getvalue()

    async def generate_chart(self, json_data) -> tuple[str, bytes]:
        return await asyncio.to_thread(self._generate_chart_sync, json_data)

    async def generate_batch(self, json_list) -> list[tuple[str, bytes]]:
        tasks = [self.generate_chart(item) for item in json_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = []
        for res in results:
            if isinstance(res, Exception):
                print(f"Error processing item: {res}")
            else:
                output.append(res)
        return output