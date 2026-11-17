# JURIST AI — Security Architecture & Data Protection

## 1. Authentication & Session Management
- **Passwords**: Salted and hashed using `bcryptjs` with a work factor of 10. Passwords are never stored or logged in plain text.
- **Tokens**: JSON Web Tokens (JWT) signed with SHA-256 (`HS256`) and an environment-isolated `JWT_SECRET`. Tokens include user ID, email, role, and expiration timestamp (default: 7 days).
- **Password Obfuscation**: The Mongoose `User` schema sets `passwordHash: { select: false }`, ensuring hashes are excluded from standard database queries.

## 2. Authorization & Data Isolation
- **Role-Based Access Control (RBAC)**: Two distinct roles: `user` (default) and `admin`. Sensitive endpoints (`/api/v1/admin/*`) are protected by `requireAuth` and `requireAdmin` middleware.
- **Tenant / User Data Isolation**: Every case creation, analysis execution, and bookmark query is strictly filtered by `userId: req.user.id`. Users cannot view, modify, or delete another user's cases.

## 3. Input Validation & Injection Defenses
- **Zod Schema Validation**: All authentication, case creation, and analysis requests are validated against strict Zod schemas before reaching business logic controllers.
- **NoSQL Injection Prevention**: Object parameters and IDs are validated through Mongoose ObjectId parsing; raw queries with unescaped `$where` or regex keys are prohibited.
- **File Validation**: Multer middleware enforces file type whitelisting (`.pdf`, `.docx`, `.txt`) and mime-type verification with a hard limit of 10MB per file.

## 4. Network & Rate Limiting
- **Helmet**: Secures HTTP headers against MIME sniffing, clickjacking, and XSS attacks.
- **Rate Limiting**:
  - Global API rate limiter: 200 requests per 15 minutes per IP.
  - Authentication limiter: 30 login/register attempts per 15 minutes per IP.
- **CORS Protection**: Whitelists configured origins (`CORS_ORIGIN`).

## 5. Environment Secrets & Zero Credentials in Git
- Credentials, tokens, and database connection strings are managed via `.env` files.
- `.gitignore` prevents tracking `.env`, `*.log`, `node_modules/`, `uploads/`, and temporary model weights.
- Template configuration provided via `.env.example` across `backend`, `frontend`, and `ml-service`.
