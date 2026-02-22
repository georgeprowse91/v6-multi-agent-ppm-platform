from __future__ import annotations


class _MetaData:
    """Minimal SQLAlchemy MetaData stub for offline environments."""

    def create_all(self, bind=None, **kwargs):
        pass

    def drop_all(self, bind=None, **kwargs):
        pass


class DeclarativeBase:
    metadata = _MetaData()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Inherit parent metadata so subclasses share the same instance.
        if "metadata" not in cls.__dict__:
            cls.metadata = DeclarativeBase.metadata


class Session:
    def __init__(self, *args, **kwargs):
        self._items: list = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add(self, obj):
        self._items.append(obj)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def query(self, *args, **kwargs):
        return _Query()

    def execute(self, *args, **kwargs):
        return _Result()

    def flush(self):
        pass

    def refresh(self, obj):
        pass

    def delete(self, obj):
        pass

    def scalar(self, *args, **kwargs):
        return None


class _Query:
    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def one_or_none(self):
        return None

    def count(self):
        return 0

    def order_by(self, *args):
        return self

    def limit(self, n):
        return self

    def offset(self, n):
        return self


class _Result:
    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def scalar_one_or_none(self):
        return None

    def scalar(self):
        return None

    def scalars(self):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def __iter__(self):
        return iter([])


class Mapped:
    def __class_getitem__(cls, item):
        return cls


def mapped_column(*args, **kwargs):
    return None


def relationship(*args, **kwargs):
    return None


def declarative_base():
    class Base:
        metadata = _MetaData()

    return Base


def sessionmaker(*args, **kwargs):
    class _SessionFactory:
        def __init__(self, *a, **kw):
            pass

        def __call__(self, *a, **kw):
            return Session()

        def __enter__(self):
            return Session()

        def __exit__(self, exc_type, exc, tb):
            return False

    return _SessionFactory
