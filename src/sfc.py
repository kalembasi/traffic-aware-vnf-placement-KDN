"""SFC catalogue and request model."""
from dataclasses import dataclass
from typing import Optional

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

# Integer encoding of SFC types used as an ML feature.
# Alphabetical order, identical to the sklearn LabelEncoder used in v1 (Video=0, VoIP=1, Web=2).
SFC_CODES = {name: i for i, name in enumerate(sorted(SFC_CATALOG))}


@dataclass
class SFCRequest:
    """A single SFC request arriving at the orchestrator."""
    req_id: int
    sfc_type: str
    arrival: float
    duration: float
    src: Optional[str] = None   # ingress node (unused by the v1 latency model)
    dst: Optional[str] = None   # egress node (unused by the v1 latency model)

    @property
    def chain(self):
        return SFC_CATALOG[self.sfc_type]

    @property
    def bandwidth(self):
        return SFC_BANDWIDTH[self.sfc_type]
