# Database Schema

SQLite database, auto-created on first startup.

## Tables

### users
| Column        | Type    | Constraints                       |
|---------------|---------|-----------------------------------|
| id            | INTEGER | PRIMARY KEY                       |
| username      | TEXT    | UNIQUE, NOT NULL                  |
| email         | TEXT    | UNIQUE (nullable)                 |
| password_hash | TEXT    | NOT NULL (bcrypt)                 |
| display_name  | TEXT    | NOT NULL DEFAULT ''               |
| created_at    | TEXT    | NOT NULL DEFAULT datetime('now')  |

### boards
| Column      | Type    | Constraints                                          |
|-------------|---------|------------------------------------------------------|
| id          | INTEGER | PRIMARY KEY                                          |
| user_id     | INTEGER | NOT NULL, FK -> users(id) ON DELETE CASCADE          |
| name        | TEXT    | NOT NULL                                             |
| description | TEXT    | NOT NULL DEFAULT ''                                  |
| position    | INTEGER | NOT NULL DEFAULT 0 (ordering within a user's list)   |
| created_at  | TEXT    | NOT NULL DEFAULT datetime('now')                     |
| updated_at  | TEXT    | NOT NULL DEFAULT datetime('now')                     |

### columns
| Column   | Type    | Constraints                                          |
|----------|---------|------------------------------------------------------|
| id       | INTEGER | PRIMARY KEY                                          |
| board_id | INTEGER | NOT NULL, FK -> boards(id) ON DELETE CASCADE         |
| title    | TEXT    | NOT NULL                                             |
| position | INTEGER | NOT NULL                                             |

### cards
| Column     | Type    | Constraints                                          |
|------------|---------|------------------------------------------------------|
| id         | INTEGER | PRIMARY KEY                                          |
| column_id  | INTEGER | NOT NULL, FK -> columns(id) ON DELETE CASCADE        |
| title      | TEXT    | NOT NULL                                             |
| details    | TEXT    | NOT NULL DEFAULT ''                                  |
| position   | INTEGER | NOT NULL                                             |
| created_at | TEXT    | NOT NULL DEFAULT datetime('now')                     |
| updated_at | TEXT    | NOT NULL DEFAULT datetime('now')                     |

## Relationships

- A **user** has many **boards**.
- A **board** has many **columns**.
- A **column** has many **cards**.
- Ordering is managed via integer `position` on boards, columns, and cards.

## Design decisions

- **Password hashing**: bcrypt via the `bcrypt` package. Raw passwords are never stored.
- **Email optional**: registration accepts an email but does not require one. Emails are unique when present.
- **Explicit boards table**: each user has one or more boards. On first login a user is seeded with a default board containing the default columns and sample cards.
- **Cascading deletes**: deleting a user tears down their boards; deleting a board tears down its columns and cards. The app also deletes children explicitly so the behaviour holds even if `PRAGMA foreign_keys=ON` is not active.
- **Timestamps**: `created_at`/`updated_at` use SQLite `datetime('now')` for simplicity. Mutation helpers update `updated_at` on the parent board when its content changes.
- **Integer positions**: renumbered on move/delete to stay sequential.

## Default seed data

The backend seeds a demo account (`user` / `password`) with display name
"Demo User" on startup, and a single default board named "My Board" populated
with five columns (Backlog, Discovery, In Progress, Review, Done) and eight
sample cards. New boards created via the API get the five default columns but
no cards.
