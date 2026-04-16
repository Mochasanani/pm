# Database Schema

SQLite database, auto-created on first startup.

## Tables

### users
| Column   | Type    | Constraints       |
|----------|---------|-------------------|
| id       | INTEGER | PRIMARY KEY       |
| username | TEXT    | UNIQUE, NOT NULL  |

### columns
| Column   | Type    | Constraints                    |
|----------|---------|--------------------------------|
| id       | INTEGER | PRIMARY KEY                    |
| user_id  | INTEGER | NOT NULL, FK -> users(id)      |
| title    | TEXT    | NOT NULL                       |
| position | INTEGER | NOT NULL                       |

### cards
| Column    | Type    | Constraints                    |
|-----------|---------|--------------------------------|
| id        | INTEGER | PRIMARY KEY                    |
| column_id | INTEGER | NOT NULL, FK -> columns(id)    |
| title     | TEXT    | NOT NULL                       |
| details   | TEXT    | NOT NULL, DEFAULT ''           |
| position  | INTEGER | NOT NULL                       |

## Relationships

- A **user** has many **columns** (one board per user, represented as a set of columns).
- A **column** has many **cards**.
- Ordering is managed via integer `position` fields on both columns and cards.

## Design decisions

- **Implicit board**: no separate board table. A user's board is their set of columns. Simplifies the schema for the single-board MVP while remaining extensible.
- **Integer positions**: simple ordering. On move operations, positions are renumbered to keep them sequential.
- **Multi-user ready**: `user_id` on columns supports multiple users, though the MVP uses a single hardcoded user.
- **Foreign keys with cascade**: cards are deleted when their column is deleted (though the MVP doesn't expose column deletion).
