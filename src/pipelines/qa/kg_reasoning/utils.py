from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from ....utils import ReturnInfo

class AbstractKGReasoner(ABC):

    @abstractmethod
    def perform(self, query: str) -> Tuple[str, ReturnInfo]:
        """Метод предназначен для генерации ответа на user-вопрос. Ответ обуславливается на информацию из имеющегося графа знаний.

        :param query: User-вопрос на естественном языке.
        :type query: str
        :return: Кортеж из двух объектов: (1) cгенерированный ответ; (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[str, ReturnInfo]
        """
        pass

    @abstractmethod
    def clear_kv_caches(self) -> None:
        """_summary_
        """
        pass

@dataclass
class BaseKGReasonerConfig:
    pass
