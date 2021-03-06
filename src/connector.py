"""
    SQL Connection classes and functions
"""
from typing import Optional
from abc import ABCMeta, abstractmethod
import mysql.connector
from .executor import SQLExecutor

class DBConnectionABC(metaclass=ABCMeta):
    """ SQL Connection Abstract Class """

    @abstractmethod
    def cursor(self, *args, **kwargs):
        """ Get database cursor """
        raise NotImplementedError()

    def executor(self, *args, **kwargs) -> SQLExecutor:
        """ Get libsql database executor """
        return SQLExecutor(self.cursor(*args, **kwargs))


class MySQLConnection(DBConnectionABC):
    """ MySQL Connection Class """

    def __init__(self, *args, dictionary:bool=False, named_tuple:bool=False, **kwargs):
        super().__init__()
        self.cnx = mysql.connector.connect(*args, **kwargs)
        self.cursor_dict = dictionary
        self.cursor_ntpl = named_tuple

    def commit(self):
        return self.cnx.commit()

    def cursor(self, *args, **kwargs):
        if self.cursor_dict:
            kwargs['dictionary'] = True
        if self.cursor_ntpl:
            kwargs['named_tuple'] = True
        return self.cnx.cursor(*args, **kwargs)

    def close(self) -> None:
        if self.cnx is not None:
            self.cnx.close()
            self.cnx = None

    def __exit__(self, ex_type, ex_value, trace):
        self.close()


# class DebugSQLConnection(DBConnectionABC):
#     """ Virtual Database Connection for Debugging """

#     def cursor(self, *args, **kwargs):
#         return DebugDBCursor(*args, **kwargs)

