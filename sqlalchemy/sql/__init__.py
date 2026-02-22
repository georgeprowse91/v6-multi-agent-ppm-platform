from sqlalchemy import select, text
from sqlalchemy import _SelectQuery as _SelectQuery


def delete(*args, **kwargs):
    return _SelectQuery()


def insert(*args, **kwargs):
    return _SelectQuery()


def update(*args, **kwargs):
    return _SelectQuery()
