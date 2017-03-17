class HostStatus:
  def __init__(self, host):
    self.host = host
    self.currentState = "UNKNOWN"
    self.goalState = "UNKNOWN"
    self.services = None

