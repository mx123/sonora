# Domain Events

This file defines domain Events for traceability.
Events are guaranteed facts — they represent something that has already happened.

---

## Auth Domain (DOM-0001)

<a id="EVT-0001"></a>
### EVT-0001: User Registered

- **Fact**: A user has been registered in the system.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: User
- **Triggered by**: CMD-0001 (Register User)
- **Payload**:
  - `userId` (string) — assigned user identifier
  - `email` (string) — registered email address
  - `tenantId` (string) — tenant context
  - `registeredAt` (string, ISO-8601) — registration timestamp
- **Consumers**: Tracking (for user profile reference), notification systems

<a id="EVT-0002"></a>
### EVT-0002: User Authenticated

- **Fact**: A user has successfully authenticated.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: AuthSession
- **Triggered by**: CMD-0002 (Authenticate User)
- **Payload**:
  - `userId` (string) — authenticated user identifier
  - `tenantId` (string) — tenant context
  - `sessionId` (string) — auth session identifier
  - `authMethod` (string) — authentication method used (`password`, `mfa`)
  - `authenticatedAt` (string, ISO-8601) — authentication timestamp
- **Consumers**: Audit (security event logging)

<a id="EVT-0003"></a>
### EVT-0003: Access Token Refreshed

- **Fact**: A new access token has been issued via refresh.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: AuthSession
- **Triggered by**: CMD-0003 (Refresh Access Token)
- **Payload**:
  - `userId` (string) — user identifier
  - `tenantId` (string) — tenant context
  - `sessionId` (string) — auth session identifier
  - `refreshedAt` (string, ISO-8601) — refresh timestamp
- **Consumers**: Audit (token lifecycle tracking)

<a id="EVT-0004"></a>
### EVT-0004: Refresh Token Revoked

- **Fact**: A refresh token has been invalidated.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: AuthSession
- **Triggered by**: CMD-0004 (Revoke Refresh Token)
- **Payload**:
  - `userId` (string) — user identifier
  - `tenantId` (string) — tenant context
  - `sessionId` (string) — auth session identifier
  - `reason` (string) — revocation reason
  - `revokedAt` (string, ISO-8601) — revocation timestamp
- **Consumers**: Audit (security event logging)

<a id="EVT-0005"></a>
### EVT-0005: User Activated

- **Fact**: A user account has been activated.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: User
- **Triggered by**: CMD-0005 (Activate User)
- **Payload**:
  - `userId` (string) — activated user identifier
  - `tenantId` (string) — tenant context
  - `reason` (string) — activation reason
  - `activatedAt` (string, ISO-8601) — activation timestamp
- **Consumers**: Audit (security event logging), notification systems

<a id="EVT-0006"></a>
### EVT-0006: User Deactivated

- **Fact**: A user account has been deactivated.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: User
- **Triggered by**: CMD-0006 (Deactivate User)
- **Payload**:
  - `userId` (string) — deactivated user identifier
  - `tenantId` (string) — tenant context
  - `reason` (string) — deactivation reason
  - `deactivatedAt` (string, ISO-8601) — deactivation timestamp
  - `sessionsRevoked` (integer) — number of active sessions revoked as a consequence
- **Consumers**: Audit (security event logging), notification systems


