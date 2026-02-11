# Domain Commands

This file defines domain Commands for traceability.
Commands are NOT APIs; APIs are projections of the domain.

---

## Auth Domain (DOM-0001)

<a id="CMD-0001"></a>
### CMD-0001: Register User

- **Intent**: Register a new user in the system.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: User
- **Payload**:
  - `email` (string, required) — user email address; must be unique per tenant
  - `password` (string, required) — plaintext password; hashed before storage
  - `tenantId` (string, required) — tenant context from auth token
  - `displayName` (string, optional) — user display name
- **Invariants**: BR-0001 (unique email per tenant)
- **Emits**: EVT-0001 (User Registered)
- **Error codes**: `AUTH.CREDENTIALS.INVALID`, `COMMON.VALIDATION.FAILED`, `COMMON.CONFLICT`

<a id="CMD-0002"></a>
### CMD-0002: Authenticate User

- **Intent**: Authenticate a user and issue access/refresh tokens.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: AuthSession
- **Payload**:
  - `email` (string, required) — user email address
  - `password` (string, required) — plaintext password for verification
  - `tenantId` (string, required) — tenant context
  - `authMethod` (string, optional) — authentication method (`password`, `mfa`); default: `password`
- **Invariants**: User must exist and credentials must match
- **Emits**: EVT-0002 (User Authenticated)
- **Error codes**: `AUTH.CREDENTIALS.INVALID`

<a id="CMD-0003"></a>
### CMD-0003: Refresh Access Token

- **Intent**: Issue a new access token using a valid refresh token.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: AuthSession
- **Payload**:
  - `refreshToken` (string, required) — valid refresh token
- **Invariants**: Refresh token must be valid and not revoked; auth session must be active
- **Emits**: EVT-0003 (Access Token Refreshed)
- **Error codes**: `AUTH.UNAUTHORIZED`

<a id="CMD-0004"></a>
### CMD-0004: Revoke Refresh Token

- **Intent**: Invalidate a refresh token (logout or security event).
- **Domain**: Auth (DOM-0001)
- **Aggregate**: AuthSession
- **Payload**:
  - `refreshToken` (string, required) — refresh token to revoke
  - `reason` (string, optional) — revocation reason (`user_logout`, `security_event`, `admin_action`)
- **Invariants**: Refresh token must belong to the requesting user/tenant
- **Emits**: EVT-0004 (Refresh Token Revoked)
- **Error codes**: `AUTH.UNAUTHORIZED`

<a id="CMD-0005"></a>
### CMD-0005: Activate User

- **Intent**: Activate a previously deactivated or newly registered user account.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: User
- **Payload**:
  - `userId` (string, required) — identifier of the user to activate
  - `tenantId` (string, required) — tenant context from auth token
  - `reason` (string, optional) — activation reason (`admin_action`, `email_verification`, `support_request`)
- **Invariants**: User must exist; user must not already be active
- **Emits**: EVT-0005 (User Activated)
- **Error codes**: `COMMON.NOT_FOUND`, `COMMON.CONFLICT`

<a id="CMD-0006"></a>
### CMD-0006: Deactivate User

- **Intent**: Deactivate a user account, preventing authentication.
- **Domain**: Auth (DOM-0001)
- **Aggregate**: User
- **Payload**:
  - `userId` (string, required) — identifier of the user to deactivate
  - `tenantId` (string, required) — tenant context from auth token
  - `reason` (string, optional) — deactivation reason (`admin_action`, `security_event`, `user_request`)
- **Invariants**: User must exist; user must be currently active; active sessions SHOULD be revoked
- **Emits**: EVT-0006 (User Deactivated)
- **Error codes**: `COMMON.NOT_FOUND`, `COMMON.CONFLICT`, `AUTH.UNAUTHORIZED`


