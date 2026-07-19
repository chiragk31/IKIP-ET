# Authentication.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# Purpose

This document defines the authentication and authorization architecture for the Industrial Knowledge Intelligence Platform.

Authentication verifies user identity.

Authorization determines what authenticated users are allowed to access.

The platform uses **Supabase Authentication** with JWT-based access tokens.

---

# Goals

The authentication system should

- Secure every protected endpoint
- Support email/password login
- Support OAuth providers
- Manage user sessions
- Support role-based authorization
- Integrate with Supabase Row Level Security (RLS)
- Remain provider independent

---

# Design Philosophy

Authentication is infrastructure.

Business modules should never implement authentication logic.

Every protected request must pass through an authentication layer before reaching business services.

---

# Responsibilities

Authentication is responsible for

- User Registration
- Login
- Logout
- Session Validation
- JWT Verification
- User Context
- Role Verification

Authentication is NOT responsible for

- Document Upload
- Search
- AI Copilot
- Knowledge Graph
- Asset Intelligence

---

# Architecture

```
Client

↓

Authentication Middleware

↓

JWT Verification

↓

User Context

↓

Authorization

↓

Business Service
```

---

# Folder Structure

```
backend/app/

auth/

auth_service.py

auth_router.py

jwt_handler.py

middleware.py

user_context.py

role_manager.py

permission_manager.py

auth_validator.py

models.py

schemas.py

constants.py
```

---

# Authentication Flow

```
User Login

↓

Supabase Auth

↓

JWT Token

↓

Frontend Storage

↓

API Request

↓

Authentication Middleware

↓

JWT Validation

↓

User Context

↓

Business Service
```

---

# Supported Authentication

## Email & Password

Primary authentication mechanism.

---

## OAuth

Future support

- Google
- GitHub
- Microsoft

---

## Anonymous Access

Not supported.

---

# JWT

Every authenticated request must include

```
Authorization

Bearer <token>
```

JWT is validated before reaching application logic.

---

# Session Management

The frontend stores

- Access Token
- Refresh Token
- User Information

The backend remains stateless.

---

# User Roles

Supported roles

```
Admin

Engineer

Operator

Inspector

Viewer
```

Future roles can be added without changing authentication logic.

---

# Permissions

Examples

Admin

- Full Access

Engineer

- Upload Documents
- Search
- Copilot
- Assets

Operator

- Search
- Assets
- Copilot

Inspector

- Search
- Compliance
- Reports

Viewer

- Read Only

---

# User Context

Every authenticated request receives

```json
{
  "user_id":"",
  "email":"",
  "role":"Engineer",
  "permissions":[]
}
```

Business services consume only this context.

---

# Middleware

Authentication middleware

Responsibilities

- Validate JWT
- Load User Context
- Reject Invalid Tokens
- Reject Expired Tokens

Business services never validate JWTs themselves.

---

# Authorization

Authorization occurs after authentication.

Checks include

- User Role
- Resource Access
- Required Permission

Reject unauthorized requests.

---

# Protected APIs

Require authentication

```
/documents

/assets

/search

/copilot

/dashboard

/graph
```

---

# Public APIs

May remain public

```
/health

/docs (development only)

/openapi.json (development only)
```

---

# Frontend Authentication

Use

- Supabase JS SDK
- React Context
- Protected Routes
- Axios Interceptors

Store session centrally.

---

# Route Protection

Public Routes

- Login
- Register

Protected Routes

- Dashboard
- Documents
- Assets
- Search
- Copilot

Redirect unauthenticated users to login.

---

# Token Refresh

Automatically refresh expired access tokens using Supabase Refresh Tokens.

Avoid requiring users to log in repeatedly.

---

# Logout

Logout should

- Revoke session
- Remove tokens
- Clear caches
- Redirect to login

---

# Row Level Security (RLS)

Supabase RLS should protect

- Documents
- Metadata
- User Records

Policies should enforce least privilege.

---

# Error Responses

Example

```json
{
  "success": false,
  "message": "Unauthorized",
  "errors": [
    "Invalid or expired access token."
  ]
}
```

Never expose internal authentication details.

---

# Security

Implement

- HTTPS Only
- Secure JWT Validation
- Token Expiration
- Refresh Tokens
- Input Validation
- Rate Limiting (future)

Never

- Store secrets in code
- Expose API keys
- Log JWTs

---

# Logging

Log

- Login Attempts
- Successful Logins
- Failed Logins
- Token Validation Failures
- Permission Denials
- Logout Events

Never log passwords or tokens.

---

# Performance

Implement

- Stateless Authentication
- Cached Public Keys
- Minimal JWT Parsing

Avoid unnecessary authentication lookups.

---

# Future Enhancements

Potential future capabilities

- Multi-Factor Authentication (MFA)
- Single Sign-On (SSO)
- Enterprise Identity Providers
- API Keys
- Service Accounts
- Audit Logs

---

# Recommended Architecture Improvements (Mandatory)

## Authentication Middleware

Every request should pass through

```
Client

↓

Authentication Middleware

↓

Authorization

↓

Business Service
```

Business modules must never perform authentication.

---

## User Context Pattern

Instead of exposing JWTs to business logic

Provide

```
User Context

↓

Services
```

This decouples authentication from application logic.

---

## Role-Based Access Control (RBAC)

Authorization should use

Role

↓

Permissions

↓

Resources

Avoid hardcoding role checks inside services.

---

## Provider Independence

Authentication layer should support future providers.

```
Auth Provider

↓

Supabase

Future

OAuth

SSO
```

Business modules should remain unchanged.

---

## Stateless Backend

Keep the backend stateless.

Authentication state is represented by verified JWTs and user context.

---

## Definition of Done

The authentication module is complete when

✓ User registration works.

✓ Login works.

✓ JWT validation works.

✓ User context is available.

✓ Authorization is enforced.

✓ Protected routes are secured.

✓ Role-based permissions are implemented.

✓ Logout works.

✓ Ready for production deployment.


# Architecture recommendation

I recommend adding a dedicated User Context object from the start. Rather than letting services access JWT claims directly, have the authentication middleware create a normalized context like:

{
  "user_id": "user_123",
  "email": "user@example.com",
  "role": "Engineer",
  "permissions": ["documents:read", "search:use", "copilot:chat"]
}

Every service receives this object instead of parsing tokens. This keeps your authentication concerns isolated and makes it much easier to change identity providers or permission models later without touching your business logic.

