import abc

class Rule(abc.ABC):
   
    @abc.abstractmethod
    def check_status(self):
        pass
    
    @abc.abstractmethod
    def take_action(self):
        pass
