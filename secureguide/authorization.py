"""Authorization seam for workflow-role governed operations.

The blueprint approval workflow records an ``actor`` and an ``actor_role`` on
every governed operation, but the service cannot by itself prove that the actor
is entitled to the role it claims — that is the responsibility of the auth layer
wired when a real UI or API front end is added.

This module makes that boundary explicit and injectable. ``SecureGuideService``
consults an :class:`Authorizer` before every role-gated operation. The default
:class:`TrustingAuthorizer` preserves pre-seam behavior (record the role for
audit, do not prove identity); an auth layer swaps in an authorizer that checks
real entitlements — :class:`MappingAuthorizer` is a minimal, dependency-free
example that enforces an explicit actor -> granted-roles table.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Protocol, runtime_checkable

from .errors import AuthorizationError

__all__ = ["Authorizer", "TrustingAuthorizer", "MappingAuthorizer"]


@runtime_checkable
class Authorizer(Protocol):
    """Decides whether ``actor`` may act in ``role`` for ``operation``.

    Implementations raise :class:`~secureguide.errors.AuthorizationError` to deny;
    returning normally allows the operation to proceed.
    """

    def authorize(self, actor: str, role: str, operation: str) -> None:
        ...


class TrustingAuthorizer:
    """Default seam: accepts any actor in any declared workflow role.

    The role is still recorded for audit by the service. Identity and entitlement
    verification remain the responsibility of the auth layer; until it is wired,
    this authorizer keeps the workflow usable without silently pretending that a
    real permission check has happened.
    """

    def authorize(self, actor: str, role: str, operation: str) -> None:
        return None


class MappingAuthorizer:
    """Enforce an explicit ``actor -> granted roles`` entitlement table.

    Injected once an auth layer can supply real grants (e.g. from user
    management). It proves the actor actually holds the claimed workflow role
    before a governed operation proceeds, closing the gap the default authorizer
    intentionally leaves open.
    """

    def __init__(self, grants: Mapping[str, Iterable[str]]):
        self._grants = {actor: frozenset(roles) for actor, roles in grants.items()}

    def granted_roles(self, actor: str) -> frozenset[str]:
        return self._grants.get(actor, frozenset())

    def authorize(self, actor: str, role: str, operation: str) -> None:
        granted = self._grants.get(actor)
        if not granted:
            raise AuthorizationError(f"actor '{actor}' has no granted workflow roles")
        if role not in granted:
            raise AuthorizationError(
                f"actor '{actor}' is not entitled to act as {role} "
                f"(operation: {operation})"
            )
