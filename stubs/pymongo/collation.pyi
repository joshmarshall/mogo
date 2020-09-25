from typing import Any, Optional


class Collation(object):

    def __init__(
        self, locale: str,
        caseLevel: Optional[bool] = None,
        caseFirst: Optional[str] = None,
        strength: Optional[int] = None,
        numericOrdering: Optional[bool] = None,
        alternate: Optional[str] = None,
        maxVariable: Optional[str] = None,
        normalization: Optional[bool] = None,
        backwards: Optional[bool] = None,
        **kwargs: Any) -> None: ...
