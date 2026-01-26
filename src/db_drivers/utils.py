from typing import List, Tuple, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..utils.errors import ReturnInfo

@dataclass
class BaseDatabaseConfig:
    """Базовая конфигурация для подключения к базе данных.

    :param db_info: Словарь, который должен хранить название базы данных и таблицы, к которой нужно подключиться. Значение по умолчанию {'db': 'personalaidb', 'table': 'personalaitable'}.
    :type db_info: Dict
    :param params: Набор дополнительных гиперпараметров, который необходим для подключения и настройки бд. Значения по умолчанию dict().
    :type params: Dict
    :param need_to_clear: Если True, то после успешного подключения к базе данных содержимое указанной таблицы будет удалено. Значения по умолчанию False.
    :type need_to_clear: bool
    """
    db_info: Dict = field(default_factory=lambda: {'db': 'personalaidb', 'table': 'personalaitable'})
    params: Dict = field(default_factory=lambda: dict())
    need_to_clear: bool = False

class AbstractDatabaseConnection(ABC):
    """Интерфейс, который должен поддерживать класс взаимодействия с определённой базой данных."""

    @abstractmethod
    def open_connection(self) -> ReturnInfo:
        """Метод предназначен для подключения к бд.

        :return: Статус завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """
        pass

    @abstractmethod
    def is_open(self) -> bool:
        """Метод предназначен для проверки статуса подключения к бд.

        :return: Если True, то соединение с бд есть, иначе False.
        :rtype: bool
        """
        pass

    @abstractmethod
    def close_connection(self) -> ReturnInfo:
        """Метод предназначен для разрыва соединения с бд.

        :return: Статус завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """
        pass

    @abstractmethod
    def create(self, items: List[object]) -> ReturnInfo:
        """Метод предназначен для добавления новых объектов в бд. Уникальность добавляемых объектов определяется по полю id.
        Если объект с таким id уже существует, то затирания информации не произойдёт: в бд останется прежний объект.

        :param items: Объекты на добавление.
        :type items: List[object]
        :return: Статус завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """
        pass

    @abstractmethod
    def read(self, ids: List[str]) -> List[object]:
        """Метод предназначен для получения объектов из бд по их идентификаторам. Если такого идентификатора
        не существует, то он будет пропущен.

        :param ids: Идентификаторы объектов, которые нужно получить.
        :type ids: List[str]
        :return: Список запрошенных объектов.
        :rtype: List[object]
        """
        pass

    @abstractmethod
    def update(self, items: List[object]) -> ReturnInfo:
        """Метод предназначен для обновления значений у существующих ключей. Если данного ключа нет в базе,
        то элемент будет пропущен.

        :param items: _description_
        :type items: List[object]
        :return: _description_
        :rtype: ReturnInfo
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> ReturnInfo:
        """Метод предназначен для удаления объектов из бд по их идентификаторам. Если такого идентификатора
        не существует, то он будет пропущен.

        :param ids: Идентификаторы объектов, которые нужно удалить.
        :type ids: List[object]
        :return: Статус завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """
        pass

    @abstractmethod
    def count_items(self) -> object:
        """Метод предназначен для получения суммарного количества элементов в таблице бд, к которой было выполнено подключение.

        :return: Структура данных, в которой хранится информация о количестве элементов.
        :rtype: object
        """
        pass

    @abstractmethod
    def item_exist(self, id: str) -> bool:
        """Метод предназначен для проверки на наличие объекта в бд по его идентификатору.

        :param id: Идентификатор объекта.
        :type id: str
        :return: Если объект существует, то True, иначе False.
        :rtype: bool
        """
        pass

    @abstractmethod
    def clear(self) -> ReturnInfo:
        """Метод предназначен для удаления содержания таблицы бд, к которой было выполнено подключение.

        :return: _description_
        :rtype: ReturnInfo
        """
        pass

    def __del__(self):
        # TODO
        # self.close_connection()
        pass
