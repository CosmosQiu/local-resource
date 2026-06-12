# Import all models here so Alembic auto-generation can detect them.
from app.models.user import User, Role, Permission      # noqa: F401, E402
from app.models.account import AIAccount                  # noqa: F401, E402
from app.models.compute import ComputeResource, ComputeResourceGPU  # noqa: F401, E402
from app.models.container import ContainerRequest         # noqa: F401, E402
