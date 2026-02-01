from __future__ import annotations


class _Metadata:
    def create_all(self, *args, **kwargs) -> None:
        return None


class DeclarativeBase:
    metadata = _Metadata()


class Mapped:
    def __class_getitem__(cls, item):
        return cls


class Session:
    def __init__(self, *args, **kwargs) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def add(self, *args, **kwargs) -> None:
        return None

    def commit(self) -> None:
        return None

    def refresh(self, *args, **kwargs) -> None:
        return None


def mapped_column(*args, **kwargs):
    return None

