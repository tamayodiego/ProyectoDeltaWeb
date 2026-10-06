"""SQLAlchemy table models.

Import every model here: Alembic finds tables through ``Base.metadata``, and a model
that is never imported is invisible to ``alembic revision --autogenerate``.
"""

from deltaweb.models.delta_matroid import DeltaMatroidRecord
from deltaweb.models.folder import Folder
from deltaweb.models.user import User

__all__ = ["DeltaMatroidRecord", "Folder", "User"]
