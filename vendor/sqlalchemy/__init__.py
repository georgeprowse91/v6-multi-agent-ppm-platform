"""Minimal SQLAlchemy shim for offline test environments."""

from __future__ import annotations


class _Type:
    def __init__(self, *args, **kwargs):
        pass


DateTime = Float = Integer = String = JSON = Text = Date = Numeric = _Type


class Column:
    def __init__(self, *args, primary_key: bool = False, nullable: bool = True, default=None, **kwargs):
        self.args = args
        self.primary_key = primary_key
        self.nullable = nullable
        self.default = default


class MetaData:
    def create_all(self, bind=None, **kwargs):
        pass

    def drop_all(self, bind=None, **kwargs):
        pass


class _ColumnExpression:
    """Represents a column expression; comparisons return None (no-op in stub context)."""

    def __eq__(self, other):
        return None

    def __ne__(self, other):
        return None

    def __lt__(self, other):
        return None

    def __le__(self, other):
        return None

    def __gt__(self, other):
        return None

    def __ge__(self, other):
        return None

    def __hash__(self):
        return id(self)

    def in_(self, *args, **kwargs):
        return None

    def not_in(self, *args, **kwargs):
        return None

    def ilike(self, *args, **kwargs):
        return None

    def like(self, *args, **kwargs):
        return None

    def is_(self, other):
        return None

    def is_not(self, other):
        return None

    def label(self, name):
        return self

    def asc(self):
        return self

    def desc(self):
        return self


class _ColumnProxy:
    """Proxy for Table.c column access - any attribute returns a _ColumnExpression."""

    def __getattr__(self, name):
        return _ColumnExpression()


class Table:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.c = _ColumnProxy()

    def insert(self):
        return _SelectQuery()

    def update(self):
        return _SelectQuery()

    def delete(self):
        return _SelectQuery()

    def select(self):
        return _SelectQuery()


class _Func:
    @staticmethod
    def now():
        return "now"


func = _Func()


class _Connection:
    """No-op connection stub."""

    def execute(self, *args, **kwargs):
        return _Result()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def close(self):
        pass


class _Engine:
    """No-op engine stub."""

    def connect(self):
        return _Connection()

    def begin(self):
        return _Connection()

    def execute(self, *args, **kwargs):
        return _Result()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def dispose(self):
        pass


class _Result:
    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def __iter__(self):
        return iter([])


class _SelectQuery:
    """Fluent query builder stub that no-ops all operations."""

    def where(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args):
        return self

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    def join(self, *args, **kwargs):
        return self

    def outerjoin(self, *args, **kwargs):
        return self

    def group_by(self, *args):
        return self

    def having(self, *args):
        return self

    def values(self, *args, **kwargs):
        return self

    def returning(self, *args, **kwargs):
        return self

    def on_conflict_do_update(self, *args, **kwargs):
        return self

    def on_conflict_do_nothing(self, *args, **kwargs):
        return self

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return _Result()

    def all(self):
        return []

    def first(self):
        return None

    def count(self):
        return 0


def create_engine(*args, **kwargs):
    return _Engine()


def ForeignKey(*args, **kwargs):
    return None


def select(*args, **kwargs):
    return _SelectQuery()


def text(value: str):
    return value


def engine_from_config(*args, **kwargs):
    return _Engine()


def and_(*args):
    return None


def or_(*args):
    return None


def not_(*args):
    return None


class pool:
    class NullPool:
        pass

    class StaticPool:
        pass


class exc:
    class SQLAlchemyError(Exception):
        pass

    class NoResultFound(Exception):
        pass

    class MultipleResultsFound(Exception):
        pass
