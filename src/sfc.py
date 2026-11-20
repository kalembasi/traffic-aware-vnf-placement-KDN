"""SFC catalogue and request model."""
from dataclasses import dataclass

VNF_REQUIREMENTS = {
    'NAT': {'cpu': 10, 'ram': 5},
    'Firewall': {'cpu': 10, 'ram': 5},
    'TrafficMonitor': {'cpu': 5, 'ram': 5},
    'SBC': {'cpu': 15, 'ram': 10},
    'IDS': {'cpu': 20, 'ram': 10},
    'DPI': {'cpu': 20, 'ram': 15},
    'VideoTranscoder': {'cpu': 30, 'ram': 20}
}

SFC_CATALOG = {
    'Web': ['NAT', 'Firewall', 'TrafficMonitor'],
    'VoIP': ['NAT', 'SBC', 'Firewall', 'IDS'],
    'Video': ['NAT', 'DPI', 'VideoTranscoder']
}

SFC_BANDWIDTH = {
    'Web': 10,
    'VoIP': 20,
    'Video': 50
}

SFC_CPU = {t: sum(VNF_REQUIREMENTS[v]['cpu'] for v in c) for t, c in SFC_CATALOG.items()}


@dataclass
class SFCRequest:
    """A single SFC request arriving at the orchestrator."""
    req_id: int
    sfc_type: str
    arrival: float
    duration: float
    src: str                  # ingress node
    dst: str                  # egress node
    features: dict            # observable traffic features: packets, flows
    hidden: dict              # ground truth hidden from policies: relative load r of every VNF

    @property
    def chain(self):
        return SFC_CATALOG[self.sfc_type]

    @property
    def bandwidth(self):
        return SFC_BANDWIDTH[self.sfc_type]
