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
