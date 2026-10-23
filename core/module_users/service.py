import sqlite3

from core.module_users.models import UserCreate, UserResponse
from db.connection import get_db_connection


class UserService:

    @staticmethod
    def create_user(data: UserCreate) -> UserResponse:
        with get_db_connection() as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO users (username, email, full_name)
                    VALUES (?, ?, ?)
                    """,
                    (data.username.strip(), data.email.lower().strip(), data.full_name.strip()),
                )
                user_id = cur.lastrowid
                row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                return UserResponse(**dict(row))
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: users.username" in str(e):
                    raise ValueError(f"El nombre de usuario '{data.username}' ya está registrado.") from e
                if "UNIQUE constraint failed: users.email" in str(e):
                    raise ValueError(f"El correo electrónico '{data.email}' ya está registrado.") from e
                raise ValueError("Error de integridad al crear el usuario.") from e

    @staticmethod
    def get_user_by_id(user_id: int) -> UserResponse | None:
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                return None
            return UserResponse(**dict(row))

    @staticmethod
    def get_user_by_username(username: str) -> UserResponse | None:
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if not row:
                return None
            return UserResponse(**dict(row))

    @staticmethod
    def list_users() -> list[UserResponse]:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
            return [UserResponse(**dict(r)) for r in rows]
