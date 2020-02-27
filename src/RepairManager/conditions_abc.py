import abc

class Condition(abc.ABC):
   
    @abc.abstractmethod
    def verify(self):
        pass
