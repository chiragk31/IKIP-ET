# API.md

# Industrial Knowledge Intelligence Platform

Version: 1.0

---

# API Design Principles

The backend exposes REST APIs.

All endpoints are versioned.

Base URL

/api/v1

Authentication

JWT (Supabase Access Token)

Content Type

application/json

File Upload

multipart/form-data

---

# Standard Response Format

Every endpoint returns:

Success

{
    "status": "success",
    "message": "Human readable message",
    "data": {}
}

Failure

{
    "status": "error",
    "message": "Error message",
    "errors": {}
}

---

# Authentication

All protected APIs require:

Authorization

Bearer <JWT_TOKEN>

---

# Authentication APIs

## Login

POST

/api/v1/auth/login

Body

{
    "email": "",
    "password": ""
}

Response

{
    "access_token": "",
    "refresh_token": "",
    "user": {}
}

---

## Register

POST

/api/v1/auth/register

Body

{
    "name": "",
    "email": "",
    "password": ""
}

---

## Logout

POST

/api/v1/auth/logout

---

## Current User

GET

/api/v1/auth/me

---

# Document APIs

## Upload Document

POST

/api/v1/documents/upload

Content-Type

multipart/form-data

Body

file

Response

{
    "document_id": "...",
    "status": "processing"
}

---

## Get Documents

GET

/api/v1/documents

Query Parameters

page

limit

status

type

---

## Document Details

GET

/api/v1/documents/{document_id}

---

## Delete Document

DELETE

/api/v1/documents/{document_id}

---

## Processing Status

GET

/api/v1/documents/{document_id}/status

Returns

Current Stage

Progress

Errors

---

## Reprocess Document

POST

/api/v1/documents/{document_id}/reprocess

---

# Knowledge Extraction APIs

## Trigger Extraction

POST

/api/v1/knowledge/{document_id}/extract

Query Parameters

canonical_storage_path (Required)

*Note: For manual triggers, you must provide the exact storage path of the canonical JSON generated in Epic 2. Example: `documents/2026/07/9c0fc73c_canonical_1234.json`. You can find this path by checking the Supabase dashboard in the `documents` bucket.*

original_filename (Optional)

user_id (Optional)

Returns

202 Accepted (runs in background)

---

## Get Extraction Status

GET

/api/v1/knowledge/{document_id}

Returns

Processing status and metadata

---

## Get CKO JSON

GET

/api/v1/knowledge/{document_id}/cko

Returns

The full Canonical Knowledge Object

---

# Knowledge Graph APIs

## Graph Overview

GET

/api/v1/graph

Returns

Node Count

Relationship Count

Statistics

---

## Graph Explorer

GET

/api/v1/graph/nodes

Query

search

type

---

## Graph Relationships

GET

/api/v1/graph/relationships

---

## Node Details

GET

/api/v1/graph/node/{node_id}

Returns

Properties

Neighbors

Related Documents

---

# Embeddings APIs

## Trigger Embeddings Pipeline

POST

/api/v1/embeddings/{document_id}/embed

Query Parameters

canonical_storage_path (Required)

*Note: Like the extraction API, you must provide the exact canonical JSON storage path. Example: `documents/2026/07/9c0fc73c_canonical_1234.json`. Check the Supabase `documents` bucket if you don't have it.*

Returns

202 Accepted (runs in background)

---

## Get Embeddings Status

GET

/api/v1/embeddings/{document_id}/status

Returns

Pipeline progress (chunks generated, vectors upserted)

---

# Asset APIs

## Asset List

GET

/api/v1/assets

---

## Asset Details

GET

/api/v1/assets/{asset_id}

Returns

Description

Documents

Failures

Measurements

Procedures

Risk

Graph

---

## Related Assets

GET

/api/v1/assets/{asset_id}/related

---

# Search APIs

## Semantic Search

POST

/api/v1/search

Body

{
    "query":"Bearing overheating"
}

Returns

Relevant Chunks

Documents

Score

---

## Similar Documents

GET

/api/v1/search/similar/{document_id}

---

# AI Copilot APIs

## Chat

POST

/api/v1/chat

Body

{
    "message":"Why did Pump P101 fail?"
}

Returns

{
    "answer":"",
    "citations":[],
    "related_assets":[],
    "confidence":0.93
}

---

## Conversation History

GET

/api/v1/chat/history

---

# Compliance APIs

GET

/api/v1/compliance

Returns

Violations

Missing Inspections

Expired Certificates

Recommendations

---

# Maintenance APIs

GET

/api/v1/maintenance

Returns

Failure Trends

Recommendations

Root Cause Analysis

---

# Dashboard APIs

GET

/api/v1/dashboard

Returns

Statistics

Recent Uploads

Recent Searches

Knowledge Graph Stats

Alerts

---

# User APIs

GET

/api/v1/users/profile

PUT

/api/v1/users/profile

---

# Notification APIs

GET

/api/v1/notifications

PUT

/api/v1/notifications/read

---

# Admin APIs

GET

/api/v1/admin/users

GET

/api/v1/admin/jobs

GET

/api/v1/admin/logs

POST

/api/v1/admin/reprocess

---

# Health APIs

GET

/api/v1/health

Returns

{
    "status":"healthy"
}

---

# Event Flow

Upload

↓

Document Created

↓

Inngest Event

↓

Parser

↓

OCR

↓

Knowledge Extraction

↓

Graph Update

↓

Embedding Generation

↓

Completed

---

# HTTP Status Codes

200

Success

201

Created

202

Accepted (Background Processing)

204

Deleted

400

Bad Request

401

Unauthorized

403

Forbidden

404

Not Found

409

Conflict

422

Validation Error

429

Rate Limited

500

Internal Server Error

---

# Pagination

Every list API supports

?page=1

&limit=20

Returns

{
    "page":1,
    "limit":20,
    "total":120,
    "items":[]
}

---

# Filtering

Supported query params

status

type

date

asset

user

language

---

# Sorting

sort_by

order=asc|desc

---

# Rate Limits

Authenticated Users

100 requests/minute

Anonymous

20 requests/minute

---

# API Security

JWT Required

HTTPS

Input Validation

File Validation

Request Size Limits

Role Based Access

---

# OpenAPI

Every endpoint must include

Summary

Description

Tags

Request Schema

Response Schema

Examples

FastAPI should automatically generate

/docs

and

/redoc

---

# Future APIs

WebSockets

Real-time Notifications

Streaming Chat

IoT Data

SCADA Integration

SAP Integration

Digital Twin APIs

without breaking existing REST APIs.


# Backend Structure
backend/
└── app/
    └── api/
        └── v1/
            ├── auth.py
            ├── documents.py
            ├── graph.py
            ├── assets.py
            ├── search.py
            ├── chat.py
            ├── compliance.py
            ├── maintenance.py
            ├── dashboard.py
            ├── users.py
            ├── notifications.py
            ├── admin.py
            └── health.py