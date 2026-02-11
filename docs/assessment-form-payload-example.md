# Organization Assessment Form – Complete Payload Reference

Used by **POST /assessment/submit** (multipart/form-data). All fields except `web_domain` and `documents` are required.

---

## 1. Form fields (backend names)

| Field                  | Type   | Required | Validation                          | Example                                |
| ---------------------- | ------ | -------- | ----------------------------------- | -------------------------------------- |
| `client_id`            | string | Yes      | UUID                                | `550e8400-e29b-41d4-a716-446655440000` |
| `project_id`           | string | Yes      | UUID                                | `660e8400-e29b-41d4-a716-446655440001` |
| `organization_name`    | string | Yes      | -                                   | `Apex Financial Services`              |
| `nature_of_business`   | string | Yes      | min 10 chars                        | See below                              |
| `industry_type`        | string | Yes      | Enum value                          | `Banking & Financial Services`         |
| `department`           | string | Yes      | -                                   | `Information Technology`               |
| `scope_statement_isms` | string | Yes      | min 10 chars                        | See below                              |
| `web_domain`           | string | No       | Domain if provided                  | `apexfinancial.com.my`                 |
| `documents`            | File[] | No       | PDF, DOCX, DOC, TXT, XLSX, XLS, CSV | (optional files)                       |

**Backend `industry_type` enum (use exactly):**

- `Banking & Financial Services`
- `Insurance`
- `Healthcare`
- `Technology`
- `Manufacturing`
- `Retail`
- `Government`
- `Other`

---

## 2. Complete example payload (form-field values only)

```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "660e8400-e29b-41d4-a716-446655440001",
  "organization_name": "Apex Financial Services",
  "nature_of_business": "Apex Financial Services provides retail banking, corporate lending, wealth management, and treasury services across Malaysia. We serve individuals, SMEs, and large enterprises with branch and digital channels.",
  "industry_type": "Banking & Financial Services",
  "department": "Information Technology",
  "scope_statement_isms": "The ISMS covers all information assets, personnel, and processes supporting core banking operations, including internet banking, mobile banking, branch operations, and data center infrastructure. Exclusions: third-party ATM networks and outsourced call center operations.",
  "web_domain": "apexfinancial.com.my"
}
```

---

## 3. cURL example (no documents)

Replace `<access_token>` with the Supabase session access token.

```bash
curl -X POST "http://localhost:8001/assessment/submit" \
  -H "Authorization: Bearer <access_token>" \
  -F "client_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "project_id=660e8400-e29b-41d4-a716-446655440001" \
  -F "organization_name=Apex Financial Services" \
  -F "nature_of_business=Apex Financial Services provides retail banking, corporate lending, wealth management, and treasury services across Malaysia. We serve individuals, SMEs, and large enterprises with branch and digital channels." \
  -F "industry_type=Banking & Financial Services" \
  -F "department=Information Technology" \
  -F "scope_statement_isms=The ISMS covers all information assets, personnel, and processes supporting core banking operations, including internet banking, mobile banking, branch operations, and data center infrastructure. Exclusions: third-party ATM networks and outsourced call center operations." \
  -F "web_domain=apexfinancial.com.my"
```

---

## 4. cURL example (with documents)

```bash
curl -X POST "http://localhost:8001/assessment/submit" \
  -H "Authorization: Bearer <access_token>" \
  -F "client_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "project_id=660e8400-e29b-41d4-a716-446655440001" \
  -F "organization_name=Apex Financial Services" \
  -F "nature_of_business=Apex Financial Services provides retail banking, corporate lending, wealth management, and treasury services across Malaysia. We serve individuals, SMEs, and large enterprises with branch and digital channels." \
  -F "industry_type=Banking & Financial Services" \
  -F "department=Information Technology" \
  -F "scope_statement_isms=The ISMS covers all information assets, personnel, and processes supporting core banking operations, including internet banking, mobile banking, branch operations, and data center infrastructure. Exclusions: third-party ATM networks and outsourced call center operations." \
  -F "web_domain=apexfinancial.com.my" \
  -F "documents=@/path/to/security-policy.pdf" \
  -F "documents=@/path/to/access-control.docx"
```

---

## 5. Minimal valid payload (no web_domain, no documents)

```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "660e8400-e29b-41d4-a716-446655440001",
  "organization_name": "Acme Corp",
  "nature_of_business": "We provide software and consulting services to enterprises.",
  "industry_type": "Technology",
  "department": "Information Security",
  "scope_statement_isms": "The ISMS covers all internal IT systems, cloud applications, and customer data processing."
}
```

---

## 6. Frontend → backend field mapping

| Frontend (FormData key) | Backend form parameter  |
| ----------------------- | ----------------------- |
| `organizationName`      | `organization_name`     |
| `natureOfBusiness`      | `nature_of_business`    |
| `industryType`          | `industry_type`         |
| `department`            | `department`            |
| `scopeStatementISMS`    | `scope_statement_isms`  |
| `webDomain`             | `web_domain` (optional) |
| (files)                 | `documents` (optional)  |

`client_id` and `project_id` come from the route (e.g. `/clients/[id]/projects/[projectId]/assessment`).
