"""Minimal NumPy compatibility shim for offline test environments.

When real NumPy is installed, this module transparently substitutes itself
with the real implementation.  In air-gapped / offline environments where
NumPy cannot be installed, the pure-Python fallback defined at the bottom
of this file is used instead.
"""

from __future__ import annotations

import importlib.util
import math
import os
import random as _random
import sys
from typing import Iterable, Iterator

# ---------------------------------------------------------------------------
# Attempt to load real NumPy, bypassing this stub directory.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_real_numpy() -> bool:
    """Try to load real NumPy, bypassing this stub.  Returns True on success.

    Strategy: temporarily remove this stub from sys.modules and from sys.path,
    then do a normal ``import numpy`` so Python finds the installed package
    (with all its C extensions).  On success, keep real NumPy in sys.modules
    and copy its exports into this module's namespace so existing references
    to the stub module still work.
    """
    # _THIS_DIR is the numpy/ stub directory itself.
    # A sys.path entry *p* provides this stub when os.path.join(p, "numpy")
    # resolves to _THIS_DIR.  We want to find a *different* sys.path entry
    # that contains a real numpy package.
    def _is_stub_provider(p: str) -> bool:
        return os.path.abspath(os.path.join(p, "numpy")) == _THIS_DIR

    has_real = False
    for search_path in sys.path:
        if not search_path or _is_stub_provider(search_path):
            continue
        candidate = os.path.join(search_path, "numpy", "__init__.py")
        if os.path.isfile(candidate):
            has_real = True
            break
    if not has_real:
        return False

    # Temporarily hide the stub so a fresh ``import numpy`` finds the real one.
    saved_path = sys.path[:]
    saved_numpy = sys.modules.pop("numpy", None)  # remove stub from cache
    # Remove all sys.path entries that would expose this stub
    sys.path = [p for p in sys.path if not _is_stub_provider(p)]

    try:
        import importlib as _il
        _real_numpy = _il.import_module("numpy")  # loads real numpy
        # Keep real numpy as the canonical module.
        sys.modules["numpy"] = _real_numpy
        # Update this module's namespace so attribute look-ups on the stub
        # object (held by already-imported code) get real numpy's values.
        our_globals = globals()
        for _attr in dir(_real_numpy):
            if not _attr.startswith("__"):
                our_globals[_attr] = getattr(_real_numpy, _attr)
        return True
    except Exception:
        # Reinstate the stub on failure.
        if saved_numpy is not None:
            sys.modules["numpy"] = saved_numpy
        return False
    finally:
        sys.path = saved_path


_USING_REAL_NUMPY = _load_real_numpy()

# If real NumPy was loaded, sys.modules['numpy'] now points to the real module.
# The globals of this module have been updated too, so attribute access via
# ``numpy.array`` etc. will use real NumPy.
# The fallback definitions below are only compiled when real NumPy is absent.

if not _USING_REAL_NUMPY:
    # ---------------------------------------------------------------------------
    # Pure-Python fallback (offline environments without NumPy installed)
    # ---------------------------------------------------------------------------

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
            if isinstance(idx, ndarray):
                index_vals = idx.tolist()
                # Integer fancy indexing (select elements by index).
                if self.ndim == 1:
                    return ndarray([self._data[int(i)] for i in index_vals])
                return ndarray([self._data[int(i)] for i in index_vals])
            value = self._data[idx]
            if isinstance(value, list):
                return ndarray(value)
            return value

        def __setitem__(self, idx, value) -> None:
            if isinstance(idx, ndarray):
                # Boolean mask assignment
                mask = idx.tolist()
                if self.ndim == 1:
                    for i, m in enumerate(mask):
                        if m:
                            self._data[i] = float(value)
                else:
                    for i, m in enumerate(mask):
                        if m:
                            row_len = len(self._data[i]) if isinstance(self._data[i], list) else 1
                            self._data[i] = [float(value)] * row_len
            else:
                self._data[idx] = value

        def __eq__(self, other) -> "ndarray":  # type: ignore[override]
            if self.ndim == 1:
                return ndarray([float(v == other) for v in self._data])
            return ndarray([[float(v == other) for v in row] for row in self._data])

        def __truediv__(self, other):
            if isinstance(other, ndarray):
                if self.ndim == 1 and other.ndim == 1:
                    return ndarray([a / b for a, b in zip(self._data, other._data)])
                a_2d = self._as_2d()
                b_2d = other._as_2d()
                result = []
                for r, row in enumerate(a_2d):
                    b_row = b_2d[r] if r < len(b_2d) else b_2d[0]
                    if len(b_row) == 1:
                        result.append([v / b_row[0] for v in row])
                    else:
                        result.append([a / b for a, b in zip(row, b_row)])
                return ndarray(result)
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

    def isscalar(value) -> bool:
        return isinstance(value, (int, float, bool))

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
