# CareerStep API Specification

## Base URL

```text
https://careerstep-main-api.onrender.com/api/v1
```

For protected APIs, include the access token returned from login or signup.

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

## Auth APIs

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| POST | `/auth/signup` | Create a user account | No |
| POST | `/auth/login` | Login | No |
| POST | `/auth/logout?refresh_token={refresh_token}` | Logout | No |

### Signup Request

```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User Name"
}
```

### Login Request

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

### Auth Response

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "User Name",
    "role": "USER"
  }
}
```

## Profile APIs

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| GET | `/profiles/me` | Get my profile | Required |
| PUT | `/profiles/me` | Create or update my profile | Required |

### Profile Request

```json
{
  "desired_role": "Frontend Developer",
  "skills": ["React", "TypeScript"],
  "certificates": ["Engineer Information Processing"],
  "projects": ["CareerStep"]
}
```

## Job APIs

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| GET | `/jobs` | Get job list | No |
| POST | `/jobs` | Create a job posting | Admin |
| POST | `/jobs/{job_id}/save` | Save a job posting | Required |

### Job Create Request

```json
{
  "title": "Frontend Developer",
  "company": "Company Name",
  "location": "Seoul",
  "employment_type": "Full-time",
  "skills": ["React", "TypeScript"],
  "description": "Job description"
}
```

## AI APIs

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| POST | `/ai/recommend/jobs` | Recommend jobs with AI | Required |
| POST | `/ai/essay/draft` | Generate essay draft | Required |

### Recommend Jobs Request

```json
{
  "profile": {
    "desired_role": "Frontend Developer",
    "skills": ["React", "TypeScript"],
    "certificates": [],
    "projects": ["CareerStep"]
  },
  "jobs": [
    {
      "id": 1,
      "title": "Frontend Developer",
      "company": "Company Name",
      "location": "Seoul",
      "employment_type": "Full-time",
      "skills": ["React", "TypeScript"],
      "description": "Job description"
    }
  ]
}
```

### Essay Draft Request

```json
{
  "profile": {
    "desired_role": "Frontend Developer",
    "skills": ["React", "TypeScript"],
    "certificates": [],
    "projects": ["CareerStep"]
  },
  "job_title": "Frontend Developer",
  "company": "Company Name",
  "question": "Please write the application motivation."
}
```

## Admin APIs

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| GET | `/admin/users` | Get user list | Admin |
| POST | `/admin/bootstrap` | Claim first admin role | Required |
| PATCH | `/admin/users/{user_id}/role` | Update user role | Admin |
| DELETE | `/admin/users/{user_id}` | Delete user | Admin |

### User List Response

```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "name": "User Name",
    "role": "USER",
    "created_at": "2026-06-18T16:00:00"
  }
]
```

### Update Role Request

```json
{
  "role": "ADMIN"
}
```

Allowed role values are `USER` and `ADMIN`.

## Notes

- `POST /admin/bootstrap` is available only when no admin account exists.
- The server blocks deleting your own account.
- The server blocks removing your own admin role.
- Frontend env example: `VITE_API_BASE_URL=https://careerstep-main-api.onrender.com/api/v1`
