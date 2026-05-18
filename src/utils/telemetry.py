import csv

class TelemetryLogger:
    """Logs simulation metrics state-action-reward into a CSV for ML Model Training."""
    def __init__(self, filepath):
        self.filepath = filepath
        # Initialize file and write headers
        with open(self.filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'sfc_type', 'network_active_nodes',
                'network_free_cpu', 'network_free_bw',
                'action_num_unique_nodes', 'outcome_accepted', 'outcome_latency'
            ])
            
    def log(self, timestamp, sfc_type, net_active_nodes, net_free_cpu, net_free_bw, 
            unique_nodes, accepted, latency):
        with open(self.filepath, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, sfc_type, net_active_nodes,
                net_free_cpu, net_free_bw,
                unique_nodes, accepted, latency
            ])

class DummyLogger:
    """Safe passive stand-in to pass into unmodified Engine functions when needed without standard out."""
    def info(self, msg): pass
