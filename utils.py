import importlib.util

from collections import OrderedDict
from collections.abc import Callable, Iterable, MutableMapping, Sequence
from functools import wraps
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar

from sbstudio.model.types import Coordinate3D


__all__ = (
    "constant",
    "create_path_and_open",
    "distance_sq_of",
    "simplify_path",
)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def constant(value: Any) -> Callable[..., Any]:
    

    def result(*args, **kwds):
        return value

    return result


def create_path_and_open(filename, *args, **kwds):
    
    path = Path(filename)
    path.parent.mkdir(exist_ok=True, parents=True)
    return open(str(path), *args, **kwds)


def distance_sq_of(p: Coordinate3D, q: Coordinate3D) -> float:
    
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def get_ends(items: Optional[Iterable[T]]) -> tuple[T, T] | None:
    
    if items is None:
        return None

    iterator = iter(items)
    try:
        first = last = next(iterator)
    except StopIteration:
        return None

    for item in iterator:
        last = item

    return (first, last)


def negate(func: Callable[..., bool]) -> Callable[..., bool]:
    

    @wraps(func)
    def new_func(*args, **kwds) -> bool:
        return not func(*args, **kwds)

    return new_func


def simplify_path(
    points: Sequence[T], *, eps: float, distance_func: Callable[[list[T], T, T], float]
) -> Sequence[T]:
    
    if not points:
        result = []
    else:
        
        result = _simplify_line(points, eps=eps, distance_func=distance_func)

    return points.__class__(result)


def _simplify_line(points, *, eps, distance_func):
    start, end = points[0], points[-1]
    dists = distance_func(points, start, end)
    index = max(range(len(dists)), key=dists.__getitem__)
    dmax = dists[index]

    if dmax <= eps:
        return [start, end]
    else:
        pre = _simplify_line(points[: index + 1], eps=eps, distance_func=distance_func)
        post = _simplify_line(points[index:], eps=eps, distance_func=distance_func)
        return pre[:-1] + post


def load_module(path: str) -> Any:
    
    spec = importlib.util.spec_from_file_location("colors_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LRUCache(Generic[K, V], MutableMapping[K, V]):
    

    _items: OrderedDict[K, V]

    def __init__(self, capacity: int):
        
        self._items = OrderedDict()
        self._capacity = max(int(capacity), 1)

    def __delitem__(self, key: K) -> None:
        del self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __setitem__(self, key: K, value: V):
        self._items[key] = value
        self._items.move_to_end(key)
        if len(self._items) > self._capacity:
            self._items.popitem(last=False)

    def get(self, key: K) -> V:
        
        value = self._items[key]
        self._items.move_to_end(key)
        return value

    def peek(self, key: K) -> V:
        
        return self._items[key]

    __getitem__ = peek
