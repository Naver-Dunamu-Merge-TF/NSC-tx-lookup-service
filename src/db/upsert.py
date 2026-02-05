from __future__ import annotations

from typing import Iterable

from sqlalchemy import and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql.schema import Table


def latest_wins_upsert(
    table: Table,
    values: dict,
    conflict_cols: Iterable[str],
    updated_at_col: str = "updated_at",
    ingested_at_col: str = "ingested_at",
):
    stmt = pg_insert(table).values(**values)
    conflict_cols = list(conflict_cols)

    update_columns = {
        column.name: getattr(stmt.excluded, column.name)
        for column in table.columns
        if column.name not in conflict_cols
    }

    predicate = None
    if updated_at_col in table.c and ingested_at_col in table.c:
        incoming_updated = getattr(stmt.excluded, updated_at_col)
        incoming_ingested = getattr(stmt.excluded, ingested_at_col)
        existing_updated = table.c[updated_at_col]
        existing_ingested = table.c[ingested_at_col]

        predicate = or_(
            and_(
                incoming_updated.isnot(None),
                or_(existing_updated.is_(None), incoming_updated >= existing_updated),
            ),
            and_(incoming_updated.is_(None), incoming_ingested >= existing_ingested),
        )

    return stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_=update_columns,
        where=predicate,
    )
