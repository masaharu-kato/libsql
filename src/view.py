"""
    SQL query module
"""

from typing import Any, Dict, List, Sequence, Optional, Union, Tuple, NewType
from . import fmt
from . import schema
from . import sqlexpr as sqe
from itertools import chain


ColumnName = schema.ColumnName
ColumnLike = Union[schema.Column, ColumnName]
TableName = schema.TableName
TableLike = Union[schema.Table, TableName]
ColumnAs = Union[ColumnName, Tuple[ColumnName, str]]
JoinType = NewType('JoinType', str)
OrderType = NewType('OrderType', str)
COp = NewType('COp', str) # SQL comparison operator type


class DataView(sqe.SQLExprType):
    """ Data-view class
        e.g. 
        dv = DataView(...)

        # basic
        list(dv.new('students')) # list all student records
        list(dv.new('students').eq('students', age=18)) # list students whose age is 18
        dv.new('students').id(123).one() # get a student whose id is 123

        # orders
        list(dv.new('students').order(+name, -age)) # list students with order of name ASC, age DESC
        list(dv.new('students')[+name, -age]) # same

        # groups
        list(dv.new('students').group('age')) # list of count of students grouped by `age` column

        # offset and limit
        dv.new('students')[100:] # list students (offset = 100)
        dv.new('students')[100:150] # list students (offset = 100, limit = 50)
        dv.new('students')[100::50] # list students (offset = 100, limit = 50)
    """

    def __init__(self, db:schema.Database, table:Optional[TableLike]=None, *, parent:bool=True, child:bool=True):
        self.db = db
        self._table = None
        self._colexprs = []
        self._terms = None
        self._groups = []
        self._orders = []
        self._limit = None
        self._offset = None
        self._join_parent_tables = parent
        self._join_child_tables = child

        if table:
            self.table(table)

    def new(self, table:Optional[TableLike]=None):
        """ Generate new view with table """
        return DataView(self.db, table)

    def table(self, table:TableLike):
        self._table = self.db.table(table)
        return self

    def where(self, *exprs):
        """ Append terms """
        for expr in exprs:
            self._terms = expr if self._terms is None else self._terms & expr
        return self

    def column(self, *colexprs):
        self._colexprs.extend(colexprs)
        return self

    def group(self, *columns:ColumnLike):
        """ Append group(s) """
        self._groups.extend(columns)
        return self

    def orders(self, *colexprs):
        """ Append order(s) """
        self._orders.extend(colexprs)
        return self

    def limit(self, limit:Optional[int]):
        """ Set limit """
        self._limit = limit
        return self

    def offset(self, offset:Optional[int]):
        """ Set offset """
        self._offset = offset
        return self

    def join_parents(self):
        self._join_parent_tables = True
        return self

    def join_children(self):
        self._join_child_tables = True
        return self


    def term(self, l, op, r):
        lexpr = l if isinstance(l, sqe.SQLExprType) else self.db.column(l)
        return self.where(sqe.BinaryExpr(op, lexpr, r))

    def eq(self, table:TableLike, **kwargs):
        """ Append equal terms on WHERE clause """
        table = self.db.table(table)
        for column_name, value in kwargs.items():
            self.where(table.column(column_name) == value)
        return self
        
    def id(self, idval:int):
        """ Append `id` equal term on WHERE clause """
        return self.eq(self._table, id=idval)


    def __getitem__(self, key):
        """ Append various terms """
        if isinstance(key, sqe.SQLExprType):
            return self.where(key)

        if isinstance(key, slice):
            if key.start is not None:
                self.offset(key.start)
            if key.stop is not None:
                self.limit(key.stop - (key.start or 0))
            if key.step is not None:
                self.limit(key.step)
            return self

        if isinstance(key, int): # id value
            return self.id(key)

        raise TypeError('Unexpected type.')


    def __iter__(self):
        # TODO: Implementation
        raise NotImplementedError()

    def __len__(self):
        # TODO: Implementation
        raise NotImplementedError()

    def one(self):
        # TODO: Implementation
        raise NotImplementedError()

    def pages(self) -> List['DataView']:
        # TODO: Implementation
        raise NotImplementedError()

    def __sqlout__(self, swp:sqe.SQLWithParams) -> None:

        print('id(swp)=', id(swp))

        if not self._table:
            raise RuntimeError('Table is not set.')

        # Join parent tables or/and child tables
        joins = []
        if self._join_parent_tables:
            joins.extend(self.db.table(self._table).get_parent_table_links())
        if self._join_child_tables:
            joins.extend(self.db.table(self._table).get_child_table_links())

        swp.append_clause('SELECT', [sqe.col_opt_as(col, col.opt_unique_alias()) for col in (*self._table.columns, *chain.from_iterable(table.columns for table, _ in joins), *self._colexprs)])
        swp.append_clause('FROM'  , self._table)

        for table, (lcol, rcol) in joins:
            swp.append_clause(('INNER' if lcol.not_null and rcol.not_null else 'LEFT') + ' JOIN', table, end='')
            swp.append_clause('ON', lcol == rcol)

        swp.append_clause('WHERE'   , self._terms)
        swp.append_clause('GROUP BY', self._groups)
        swp.append_clause('ORDER BY', [sqe.ordered_column(order) for order in self._orders])
        swp.append_clause('LIMIT'   , self._limit)
        swp.append_clause('OFFSET'  , self._offset)
        
        #print(swp.sql, 'params:', swp.params)
        #print('')

    def get_sql_with_params(self, default_swp:Optional[sqe.SQLWithParams]=None) -> sqe.SQLWithParams:
        swp = sqe.SQLWithParams() if default_swp is None else default_swp
        # print('generated id(swp)=', id(swp))
        swp.append(self)
        # print(swp.sql, swp.params)
        return swp


# @staticmethod
# def AUTO_ALIAS_FUNC(tablename:str, colname:str) -> str:
#     """ Automatically aliasing function for columns expressions in SELECT query """
#     return tablename[:-1] + '_' + colname


# def assert_type(value, *types):
#     """
#         Assert type of specified value
#         Specify each element of `types` to tuple of types to union type.
#         Specify `types` to the types on iterate levels.
#         e.g. list/tuple of tuple of 
#     """
#     if isinstance(, type):
#         pass