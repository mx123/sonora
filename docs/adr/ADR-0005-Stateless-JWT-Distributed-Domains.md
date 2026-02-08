# ADR-0005: Stateless JWT-based Authentication and Authorization for Distributed Domain Services

- Status: Accepted
- Date: 2026-01-25

## Context
The system is a distributed service composed of multiple independently deployed domain services (e.g., `auth`, `tenant`, `inventory`, `tracking`, `shopping-cart`).  
Despite deployment separation, a user must retain seamless (federated) access to all authorized domains during a single authentication session.

Key constraints and drivers:
- Domain services must remain **stateless**
- Authentication must be **centralized**
- Authorization must be **decentralized**
- Support for **multi-tenancy**
- Compatibility with **clustered and elastic deployments**
- Minimize runtime coupling between domains

## Decision
We adopt a **JWT-based stateless access model** with a dedicated **Auth Domain** acting as the sole token issuer.

- Short-lived **Access Tokens (JWT)** are used for all domain-to-client and inter-domain access.
- Long-lived **Refresh Tokens** are managed exclusively by the Auth Domain.
- Domain services validate JWTs locally using cached public keys (JWKS).
- Authorization decisions are made within each domain based on token claims.

## Architecture Overview
```
Client
  |
  | Access Token (JWT)
  v
API Gateway / BFF (optional)
  |
  | Access Token (JWT)
  v
------------------------------------ADR-0005
| Inventory | Cart | Tracking | ... |
------------------------------------
            ^
            |
        Auth Domain
        (Token Issuer)
```

## Token Model

### Access Token (JWT)
- TTL: 5–15 minutes
- Stateless
- Signed with asymmetric key (RS256 / ES256)
- Contains identity, tenant, and authorization claims

### Refresh Token
- Stateful
- Stored and validated only by Auth Domain
- Used to issue new access tokens

## JWT Claim Contract

### Standard Claims
```json
{
  "iss": "auth.example.com",
  "sub": "user-id",
  "aud": "distributed-service",
  "exp": 1700000000,
  "iat": 1699996400,
  "jti": "uuid"
}
```

### Context & Security Claims
```json
{
  "tenant_id": "tenant-42",
  "session_id": "auth-session-uuid",
  "auth_level": "password|mfa",
  "token_type": "access"
}
```

### Authorization Claims
```json
{
  "roles": ["USER", "ADMIN"],
  "scopes": [
    "inventory:read",
    "cart:write",
    "tracking:read"
  ]
}
```

## Responsibilities

### Auth Domain
- User authentication
- Auth session lifecycle management
- Issuance of access and refresh tokens
- JWKS publishing and key rotation
- Refresh token revocation

### Domain Services
- Local JWT validation
- Signature, issuer, audience, and expiration checks
- Tenant isolation enforcement
- Scope/role-based authorization
- No synchronous calls to Auth Domain

## Session & Revocation Strategy
- Access tokens are intentionally short-lived
- Auth session exists only in Auth Domain
- Optional compensating controls:
  - Session versioning
  - Token blacklist for high-risk events

## Multi-Tenancy Model
- `tenant_id` is a mandatory claim
- Cross-tenant access is forbidden by default
- Domains must not trust client-supplied tenant context

## Security Considerations
- Zero-trust between services
- No shared session storage
- No domain-specific business data in JWT
- API Gateway does not replace domain-level authorization

## Consequences

### Positive
- Horizontally scalable stateless domains
- Clear separation of concerns
- Minimal runtime coupling
- Suitable for Kubernetes / clustered environments

### Negative
- Token revocation is eventual, not immediate
- JWT size must be carefully controlled
- Requires disciplined claim governance

## Alternatives Considered
- Centralized session store (rejected: breaks statelessness)
- Per-domain authentication (rejected: poor UX and coupling)
- Long-lived access tokens (rejected: security risk)

## Notes
This ADR is compatible with OAuth 2.0 / OpenID Connect profiles and can be implemented using any stack that supports JWT validation and JWKS key distribution.
