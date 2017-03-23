class ServiceStatus:
  def __init__(self, name, state, loadState="Unknown", activeState="Unknown"):
     self.name = name
     self.state = state               # may also be formally known as substate in fleet
     self.loadState = loadState
     self.activeState = activeState
