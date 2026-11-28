from dataclasses import dataclass

from fastapi import Query


@dataclass(frozen=True)
class PageParams:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)) -> PageParams:
    return PageParams(page=page, size=size)


def page_body(items: list, total: int, params: PageParams) -> dict:
    return {"items": items, "total": total, "page": params.page, "size": params.size}
