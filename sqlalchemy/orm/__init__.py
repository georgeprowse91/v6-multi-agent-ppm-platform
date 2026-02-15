from __future__ import annotations


class DeclarativeBase:
    pass


class Session:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class Mapped:
    def __class_getitem__(cls, item):
        return cls


def mapped_column(*args, **kwargs):
    return None


def declarative_base():
    class Base:
        pass

    return Base


def sessionmaker(*args, **kwargs):
    return Session
