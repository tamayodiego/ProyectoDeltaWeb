"""SQLAlchemy table models.

Import every model here: Alembic finds tables through ``Base.metadata``, and a model
that is never imported is invisible to ``alembic revision --autogenerate``.
"""

from deltaweb.models.user import User

__all__ = ["User"]
