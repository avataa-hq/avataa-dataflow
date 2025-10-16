from abc import ABC, abstractmethod


class ABCManager(ABC):
    @abstractmethod
    def check_connection(self):
        pass

    @abstractmethod
    def listdir(self):
        raise NotImplementedError("Operation not supported!")
