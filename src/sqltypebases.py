""" SQL build-in data types """
import types
import typing
from functools import lru_cache
from . import record


def is_child_class(target, base):
    return issubclass(target, base) and target is not base


def _isinstance(v, t):
    assert isinstance(t, type)
    return isinstance(v, t)


class _IntValueType:
    """ Int value type """
    _VALUE_ = None

def _int_value_type(v:int):
    if not isinstance(v, int):
        raise TypeError('`v` is not an integer.')
    return types.new_class('intv_{}'.format(v), bases=(_IntValueType,))



class SQLType:
    """ SQL data types """
    _PY_TYPE_      : typing.Optional[typing.Type] = None # Corresponding python type
    __TYPE_SQL__   : typing.Optional[str]  = None # Code of this type in SQL. Specify None if it is the same as the class name
    _TYPE_HAS_DEFAULT_ : bool = True # Type has a default value
    _TYPE_DEFAULT_VALUE_ : typing.Any = None # Type's default value (if has)
    _TYPE_COMMENT_ : str = None # Type's comment

    def __init__(self, v):
        self.v = v

    @classmethod
    def _validate_value(cls, _): # Default implementation
        return True 

    @classmethod
    def __type_sql__(cls): # Default implementation
        assert issubclass(cls, Final)
        return cls.__TYPE_SQL__ or cls.__name__.upper()

    @typing.final
    @classmethod
    def validate_value(cls, v):
        """ Validate a given value """
        assert cls._PY_TYPE_ is not None
        return _isinstance(v, cls._PY_TYPE_) and cls._validate_value(v)

    @typing.final
    def validate(self):
        """ Validate a given value (with type check) """
        return self.validate_value(self.v)

    @classmethod
    def default(cls, *args):
        """ Set/clear default value """
        if len(args) > 1:
            raise RuntimeError('Cannot specify multiple arguments.')
        if len(args):
            cls._TYPE_HAS_DEFAULT_ = True
            cls._TYPE_DEFAULT_VALUE_ = args[0]
        else:
            cls._TYPE_HAS_DEFAULT_ = False
            cls._TYPE_DEFAULT_VALUE_ = None

    @classmethod
    def has_default_value(cls):
        """ Get this type has a default value or not """
        return cls._TYPE_HAS_DEFAULT_

    @classmethod
    def default_value(cls):
        """ Get the default value (if exists) """
        if not cls.has_default_value():
            raise RuntimeError('This type does not have a default value.')
        return cls._TYPE_DEFAULT_VALUE_

    @classmethod
    def comment(cls, comment=None):
        """ Set comment """
        cls._TYPE_COMMENT_ = comment

    @classmethod
    def get_comment(cls):
        """ Get comment """
        return cls._TYPE_COMMENT_



def get_type_sql(t):
    """ Get the SQL of type in a given SQLType subclass """
    assert issubclass(t, SQLType)
    return t.__type_sql__()


class SQLGenericType:
    """ SQL generic data types """


class SQLTypeWithOptionalKey(SQLGenericType):
    """ SQL data type with key (length or value(s) etc.) """
    _TYPE_HAS_KEY_ = False

    @classmethod
    def new_subclass(cls, classname:str, bases=None, **classprops):
        """ Create a new subclass (using a given key) """
        return types.new_class(
            classname,
            (cls, *(bases or [])),
            {},
            lambda ns: ns.update({'_TYPE_HAS_KEY_': True, **classprops})
        )


class SQLTypeWithKey(SQLTypeWithOptionalKey):
    """ SQL data type with key (length or value(s) etc.) """

    def __new__(cls, *_args, **_kwargs):
        if not cls._TYPE_HAS_KEY_:
            raise RuntimeError('Generic type key is not specified.')
        return super().__new__(cls)


class SQLTypeWithOptionalLength(SQLTypeWithOptionalKey):
    """ SQL data types with optional length """
    _MAX_LEN_ = None

    @classmethod
    @lru_cache
    def __class_getitem__(cls, l):
        assert isinstance(l, int) and issubclass(cls, SQLType)
        return cls.new_subclass(
            f'{cls.__name__}_len{l}',
            _MAX_LEN_ = l,
            __TYPE_SQL__ = f'{get_type_sql(cls)}({l})',
        )


class SQLTypeWithLength(SQLTypeWithOptionalLength, SQLTypeWithKey):
    """ SQL data types with length (required) """

class NumericType(SQLType):
    """ Numeric types """

class IntegerType(NumericType):
    """ Integer types """
    _PY_TYPE_ = int
    _MIN_VALUE_ = None
    _MAX_VALUE_ = None

    @classmethod
    def _validate_value(cls, v):
        return cls._MIN_VALUE_ <= v and v <= cls._MAX_VALUE_

    def __int__(self):
        return int(self.v)

class UnsignedIntegerType(IntegerType):
    """ Unsigned integer types """
    _MIN_VALUE_ = 0


class FloatType(NumericType):
    """ Floating-point decimal types """
    _PY_TYPE_ = float

    def __float__(self):
        return float(self.v)


class DecimalType(NumericType, SQLTypeWithKey):
    """ Fixed Decimal types """
    _TYPE_DECI_PREC_  : typing.Optional[int] = None
    _TYPE_DECI_SCALE_ : typing.Optional[int] = None

    @classmethod
    @lru_cache
    def __class_getitem__(cls, pr_sc): # Precision and scale
        assert isinstance(pr_sc, tuple) and len(pr_sc) == 2 and isinstance(pr_sc[0], int) and isinstance(pr_sc[1], int)
        pr, sc = pr_sc
        return cls.new_subclass(
            f'{cls.__name__}_{pr}_{sc}',
            _TYPE_DECI_PREC_  = pr,
            _TYPE_DECI_SCALE_ = sc,
        )

    def __new__(cls, *_args, **_kwargs):
        if not cls._TYPE_DECI_PREC_ or not cls._TYPE_DECI_SCALE_:
            raise RuntimeError('Precisoin and/or scale is not specified.')
        return super().__new__(cls)


class DatetimeType(SQLType):
    """ Date and time types """


class StringType(SQLType):
    """ String types """
    _PY_TYPE_ = str
    _MAX_LEN_ = None

    def __str__(self):
        return str(self.v)


class CharType(StringType, SQLTypeWithLength):
    """ Char types (with required length) """
    @classmethod
    def _validate_value(cls, v):
        return len(v) <= cls._MAX_LEN_


class TextType(StringType, SQLTypeWithOptionalLength):
    """ Text types (with optional length) """
    @classmethod
    def _validate_value(cls, v):
        return not cls._MAX_LEN_ or len(v) <= cls._MAX_LEN_


class SQLTypeWithValues(SQLTypeWithKey):
    """ SQL data types with optional length """
    _TYPE_VALUES_ = None

    @classmethod
    @lru_cache
    def __class_getitem__(cls, values):
        assert isinstance(values, tuple) and all(isinstance(v, str) for v in values)
        return cls.new_subclass(
            f'{cls.__name__}_vals_' + '_'.join(values),
            _TYPE_VALUES_ = values,
            __TYPE_SQL__  = f'{get_type_sql(cls)}(' + ', '.join(f"'{v}'" for v in values) + ')',
        )


class Record:
    """ Record class (declaration) """


class SQLTypeEnv:
    """ SQL Type environment definition """
    type_aliases = {}
    default_not_null = True

    def __new__(cls, *args, **kwargs):
        raise RuntimeError('This class cannot be initialized.')

    @classmethod
    def set_type_alias(cls, tf:typing.Type, tt:typing.Type):
        """ Set an alias type of a given type """
        assert is_child_class(tt, SQLType)
        cls.type_aliases[tf] = tt

    @staticmethod
    def _is_typing_type(t):
        return typing.get_origin(t) is not None

    @staticmethod
    def _is_typing_optional(t):
        if typing.get_origin(t) is typing.Union:
            tpargs = typing.get_args(t)
            return len(tpargs) == 2 and tpargs[1] is type(None)

    @staticmethod
    def _typing_optional_basetype(t):
        return t.__args__[0]

    @classmethod
    def actual_type(cls, t, *, ensure_nullable:bool=False):
        """ Get an actual type (subclass of SQLType) of a given type """
        if cls._is_typing_optional(t):
            return cls.actual_type(cls._typing_optional_basetype(t), ensure_nullable=False)
        if is_child_class(t, Record):
            return ForeignTableKey[t]
        if t in cls.type_aliases:
            t = cls.type_aliases.get(t)
        if ensure_nullable and cls.default_not_null and not issubclass(t, (Nullable, NotNull)):
            t = NotNull[t]
        return t

    @classmethod
    def is_compatible_type(cls, t):
        if cls._is_typing_type(t):
            return cls._is_typing_optional(t)
        return is_child_class(t, SQLType) or is_child_class(t, Record) or t in cls.type_aliases

    @classmethod
    def type_sql(cls, t) -> str:
        """ Get a SQL of type for table creation """
        t = cls.actual_type(t)
        return t.__type_sql__()


class SQLTypeWithType(SQLTypeWithKey):
    """ SQL data types with optional length """
    _TYPE_BASE_ = None
    _TYPE_SQL_SUFFIX_ = None
    _TYPE_ENSURE_NULLABLE_ = False

    @classmethod
    @lru_cache
    def __class_getitem__(cls, t):
        assert cls._TYPE_SQL_SUFFIX_ is not None
        assert isinstance(t, type)
        t = SQLTypeEnv.actual_type(t, ensure_nullable=cls._TYPE_ENSURE_NULLABLE_)
        return cls.new_subclass(
            f'{cls.__name__}__{t.__name__}',
            (t,),
            _TYPE_BASE_  = t,
            __TYPE_SQL__ = t.__type_sql__() + cls._TYPE_SQL_SUFFIX_,
        )


class Final:
    """ Represents the class is final (= actual SQL type) """


class Int(Final, IntegerType):
    """ Normal Int type """
    _MIN_VALUE_ = -2**31
    _MAX_VALUE_ = 2**31-1


class Nullable(Final, SQLTypeWithType):
    """ SQL optional type """
    _TYPE_SQL_SUFFIX_ = ''


class NotNull(Final, SQLTypeWithType):
    """ SQL NOT NULL type """
    _TYPE_SQL_SUFFIX_ = ' NOT NULL'
    _TYPE_HAS_DEFAULT_ = False
    _TYPE_DEFAULT_VALUE_ = None


class PrimaryKey(Final, SQLTypeWithType):
    """ SQL Primary Key type """
    _TYPE_SQL_SUFFIX_ = ' PRIMARY KEY'
    _TYPE_ENSURE_NULLABLE_ = True


class ForeignTableKey(Final, SQLTypeWithType):
    """ Foreign table key (Primary key) """

    @classmethod
    @lru_cache
    def __class_getitem__(cls, t):
        assert issubclass(t, record.Record)
        return cls.new_subclass(
            f'FK__{t.__name__}',
            (Int,),
            _TYPE_BASE_  = t,
            __TYPE_SQL__ = Int.__type_sql__(),
        )


# class RecordEnv(SQLTypeEnv):
#     """ Record definition environment class """

#     common_columns = {
#         'id' : PrimaryKey[NotNull[Int]],
#     }

#     @classmethod
#     def set_common_columns(cls, tf:Type, tt:Type):
#         """ Set a common columns """
#         assert isinstance(tt, SQLType)
#         cls.common_columns[tf] = tt
