"""
Casbin RBAC enforcer — loaded once at startup, used for permission checks.

Default model: RBAC with domains (domain = resource_type).
Policies are loaded from DB via a custom adapter or from a file.

For now, permission checks are done via the JWT token scopes + DB roles;
Casbin integration can be deepened later by loading policies from DB.
"""
import casbin
from casbin import persist

from app.core.config import settings

# Inline Casbin model definition (RBAC with domains)
CASBIN_MODEL_CONF = """
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub, r.dom) && r.dom == p.dom && r.obj == p.obj && r.act == p.act
"""

_enforcer: casbin.Enforcer | None = None


def get_enforcer() -> casbin.Enforcer:
    """Get or create the Casbin enforcer singleton."""
    global _enforcer
    if _enforcer is None:
        adapter = persist.file_adapter.FileAdapter("casbin_policy.csv")
        _enforcer = casbin.Enforcer(
            model=casbin.Model(CASBIN_MODEL_CONF),
            adapter=adapter,
            enable_log=settings.APP_DEBUG,
        )
    return _enforcer


def enforce(user_id: str, resource_type: str, obj: str, act: str) -> bool:
    """Check if user has permission via Casbin."""
    return get_enforcer().enforce(user_id, resource_type, obj, act)


def add_role_for_user(user_id: str, role: str, domain: str = "*") -> bool:
    """Grant a role to a user in a domain."""
    return get_enforcer().add_role_for_user(user_id, role, domain)


def add_permission_for_role(role: str, domain: str, obj: str, act: str) -> bool:
    """Add a permission to a role."""
    return get_enforcer().add_policy(role, domain, obj, act)
