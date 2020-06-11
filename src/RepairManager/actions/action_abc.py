import abc


class Action(abc.ABC):
    @abc.abstractmethod
    def execute(self):
        pass
