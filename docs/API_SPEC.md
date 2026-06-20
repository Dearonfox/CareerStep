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
| POST | `/auth/refresh` | Exchange a refresh token for a new access/refresh token pair | No |
| POST | `/auth/logout?refresh_token={refresh_token}` | Logout | No |

### Refresh Request

```json
{
  "refresh_token": "..."
}
```

The response shape is identical to the Auth Response below. The refresh token is rotated on every call —
the old refresh token is invalidated immediately, so each token can only be used once.

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
| PUT | `/profiles/me` | Create or update my profile (basic spec fields) | Required |
| POST | `/profiles/me/resume` | Upload a resume PDF, parse it via AI, and merge the result into my profile | Required |
| POST | `/profiles/me/transcript` | Submit pasted transcript text, parse it via AI, and merge the result into my profile | Required |
| POST | `/profiles/me/portfolio` | Submit pasted portfolio text, parse it via AI, and merge the result into my profile | Required |

### Profile Request

```json
{
  "desired_role": "Frontend Developer",
  "skills": ["React", "TypeScript"],
  "certificates": ["Engineer Information Processing"],
  "projects": ["CareerStep"]
}
```

### Resume Upload Request

`multipart/form-data` with a single `file` field containing a PDF (max 10MB, text-based PDFs only —
image-only PDFs are rejected with `422`).

### Transcript Request

```json
{
  "transcript_text": "1학년 1학기 ... (붙여넣은 성적표 텍스트)"
}
```

### Portfolio Request

```json
{
  "portfolio_text": "프로젝트명: ... (붙여넣은 포트폴리오 텍스트)"
}
```

### Profile Response (full shape returned by GET/PUT/resume/transcript/portfolio)

All three upload endpoints return the same `ProfileRead` shape — each call only overwrites the fields
it parses and leaves the rest untouched.

```json
{
  "id": 1,
  "user_id": 1,
  "desired_role": "Backend Developer",
  "skills": ["Python", "FastAPI"],
  "certificates": ["자격증: 정보처리기사", "어학: TOEIC 900"],
  "projects": ["CareerStep (Python, FastAPI)"],
  "target_roles": ["Backend Developer", "DevOps Engineer"],
  "career_level": "신입",
  "skills_detail": {
    "languages": ["Python"],
    "frameworks": ["FastAPI"],
    "databases": ["MySQL"],
    "cloud_devops": [],
    "tools": [],
    "others": []
  },
  "education": [{ "school": "전북대학교", "major": "컴퓨터인공지능학부", "degree": "학사", "graduation_status": "재학" }],
  "experience": [],
  "projects_detail": [{ "name": "CareerStep", "summary": "...", "technologies": ["Python", "FastAPI"], "period": "2026", "role": "백엔드", "outcomes": [] }],
  "gpa": "4.0",
  "gpa_scale": "4.5",
  "transcript_strong_subjects": [{ "name": "자료구조", "grade": "A+", "relevance": "high" }],
  "transcript_weak_subjects": [],
  "total_credits": "120",
  "completed_semesters": "6",
  "portfolio_projects": [{ "name": "CareerStep", "period": "2026.01-2026.06", "duration_months": 6, "team_type": "팀", "team_size": 4, "my_role": "백엔드", "contribution_percent": 40, "technologies": ["Python"], "is_deployed": true, "deploy_url": "https://...", "outcomes": [] }],
  "portfolio_total_count": 1,
  "portfolio_solo_count": 0,
  "portfolio_team_count": 1,
  "portfolio_deployed_count": 1,
  "portfolio_total_months": 6
}
```

## Preference APIs

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| GET | `/preferences/me` | Get my job-search preferences | Required |
| PUT | `/preferences/me` | Create or update my job-search preferences | Required |

### Preference Request

```json
{
  "job_roles": ["백엔드 개발자"],
  "company_types": ["스타트업", "중견기업"],
  "preferred_regions": ["서울", "경기"],
  "target_timeline": "6개월 이내",
  "weekly_hours": 20,
  "wants_cert_upgrade": true,
  "priority_area": "기술스택"
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
