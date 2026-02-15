"""Minimal NumPy compatibility shim for offline test environments."""

from __future__ import annotations

import math
import random as _random
from typing import Iterable, Iterator


float32 = float
bool_ = bool
int_ = int
float64 = float


class ndarray:
    def __init__(self, data):
        self._data = _clone(data)

    @property
    def ndim(self) -> int:
        return 2 if self._data and isinstance(self._data[0], list) else 1

    @property
    def shape(self) -> tuple[int, ...]:
        if self.ndim == 2:
            return (len(self._data), len(self._data[0]) if self._data else 0)
        return (len(self._data),)

    @property
    def size(self) -> int:
        if self.ndim == 2:
            return self.shape[0] * self.shape[1]
        return len(self._data)

    @property
    def T(self) -> "ndarray":
        if self.ndim == 1:
            return ndarray([[v] for v in self._data])
        rows, cols = self.shape
        return ndarray([[self._data[r][c] for r in range(rows)] for c in range(cols)])

    def astype(self, _dtype) -> "ndarray":
        return ndarray(self._data)

    def reshape(self, rows: int, cols: int) -> "ndarray":
        flat = self._flatten()
        if rows == 1 and cols == -1:
            return ndarray([flat])
        if rows * cols != len(flat):
            raise ValueError("invalid reshape")
        return ndarray([flat[r * cols : (r + 1) * cols] for r in range(rows)])

    def tobytes(self) -> bytes:
        return repr(self._data).encode("utf-8")

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator:
        if self.ndim == 2:
            for row in self._data:
                yield ndarray(row)
        else:
            yield from self._data

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return ndarray(self._data[idx])
        value = self._data[idx]
        if isinstance(value, list):
            return ndarray(value)
        return value

    def __setitem__(self, idx, value) -> None:
        self._data[idx] = value

    def __truediv__(self, other):
        if isinstance(other, ndarray):
            if self.ndim == 1:
                return ndarray([a / b for a, b in zip(self._data, other._data)])
            return ndarray(
                [[a / b for a, b in zip(row, other._data[r])] for r, row in enumerate(self._data)]
            )
        if self.ndim == 1:
            return ndarray([v / other for v in self._data])
        return ndarray([[v / other for v in row] for row in self._data])

    def __matmul__(self, other):
        a = self._as_2d()
        b = other._as_2d()
        cols = len(b[0]) if b else 0
        result = []
        for arow in a:
            out = []
            for c in range(cols):
                out.append(sum(arow[k] * b[k][c] for k in range(len(arow))))
            result.append(out)
        return ndarray(result)

    def _as_2d(self) -> list[list[float]]:
        if self.ndim == 1:
            return [list(self._data)]
        return [list(row) for row in self._data]

    def _flatten(self) -> list[float]:
        if self.ndim == 1:
            return list(self._data)
        flat: list[float] = []
        for row in self._data:
            flat.extend(row)
        return flat

    def tolist(self):
        return _clone(self._data)


def _clone(data):
    if isinstance(data, ndarray):
        return _clone(data._data)
    if isinstance(data, list):
        return [_clone(x) for x in data]
    if isinstance(data, tuple):
        return [_clone(x) for x in data]
    return float(data)


def array(data, dtype=None) -> ndarray:
    return ndarray(data)


def asarray(data, dtype=None) -> ndarray:
    return ndarray(data)


def empty(shape, dtype=None) -> ndarray:
    rows, cols = shape
    return ndarray([[0.0 for _ in range(cols)] for _ in range(rows)])


def vstack(values: Iterable) -> ndarray:
    rows = []
    for value in values:
        if isinstance(value, ndarray):
            if value.ndim == 1:
                rows.append(value.tolist())
            else:
                rows.extend(value.tolist())
        else:
            rows.append(list(value))
    return ndarray(rows)


def delete(values: ndarray, row: int, axis: int = 0) -> ndarray:
    data = values.tolist()
    if axis != 0:
        raise ValueError("only axis=0 supported")
    data.pop(row)
    return ndarray(data)


def argpartition(values: ndarray, kth: int) -> ndarray:
    pairs = sorted(enumerate(values.tolist()), key=lambda item: item[1])
    return ndarray([idx for idx, _ in pairs])


def argsort(values: ndarray) -> ndarray:
    pairs = sorted(enumerate(values.tolist()), key=lambda item: item[1])
    return ndarray([idx for idx, _ in pairs])


def round(values: ndarray, decimals: int = 0) -> ndarray:
    factor = 10**decimals
    if values.ndim == 1:
        return ndarray([math.floor(v * factor + 0.5) / factor for v in values.tolist()])
    return ndarray(
        [[math.floor(v * factor + 0.5) / factor for v in row] for row in values.tolist()]
    )


class _Linalg:
    @staticmethod
    def norm(values: ndarray, axis: int | None = None, keepdims: bool = False):
        data = values.tolist() if isinstance(values, ndarray) else values
        if axis is None:
            if data and isinstance(data[0], list):
                flat = [x for row in data for x in row]
            else:
                flat = data
            return math.sqrt(sum(v * v for v in flat))
        if axis == 1:
            norms = [math.sqrt(sum(v * v for v in row)) for row in data]
            if keepdims:
                return ndarray([[v] for v in norms])
            return ndarray(norms)
        raise ValueError("unsupported axis")


linalg = _Linalg()


class _Rng:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = _random.Random(seed)

    def random(self, shape, dtype=None) -> ndarray:
        rows, cols = shape
        return ndarray([[self._rng.random() for _ in range(cols)] for _ in range(rows)])


class _Random:
    @staticmethod
    def default_rng(seed: int | None = None) -> _Rng:
        return _Rng(seed)


random = _Random()


def isscalar(value) -> bool:
    return isinstance(value, (int, float, bool))
