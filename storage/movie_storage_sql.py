"""
storage/movie_storage_sql.py - SQLite storage using SQLAlchemy (raw SQL via text()).

User profiles:
- users table
- movies linked to users via user_id (FK)

Public API:
- list_users() -> list[tuple[int, str]]
- create_user(name) -> int
- get_user_id(name) -> int | None

- get_movies(user_id) -> dict
- add_movie(user_id, title, year, rating, poster)
- delete_movie(user_id, title)
- update_movie(user_id, title, rating)
"""

from __future__ import annotations

from typing import Dict, TypedDict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


class MovieRecord(TypedDict):
  year: int
  rating: float
  poster: str


MovieData = Dict[str, MovieRecord]

DB_URL = "sqlite:///data/movies.db"
engine = create_engine(DB_URL, echo=False, future=True)


def _init_db() -> None:
  """Create tables if they do not exist."""
  with engine.begin() as connection:
    # Users
    connection.execute(text("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
      )
    """))

    # Movies linked to users
    connection.execute(text("""
      CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        year INTEGER NOT NULL,
        rating REAL NOT NULL,
        poster TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, title)
      )
    """))


_init_db()


# ---------- Users ----------

def list_users() -> List[Tuple[int, str]]:
  """Return list of (id, name)."""
  with engine.connect() as connection:
    result = connection.execute(text("SELECT id, name FROM users ORDER BY name"))
    return [(int(r[0]), str(r[1])) for r in result.fetchall()]


def create_user(name: str) -> int:
  """Create user and return its id."""
  try:
    with engine.begin() as connection:
      connection.execute(
        text("INSERT INTO users (name) VALUES (:name)"),
        {"name": name},
      )
  except IntegrityError:
    raise ValueError("User existiert bereits.") from None

  user_id = get_user_id(name)
  if user_id is None:
    raise RuntimeError("User konnte nicht erstellt werden.")
  return user_id


def get_user_id(name: str) -> Optional[int]:
  """Get user id by name."""
  with engine.connect() as connection:
    result = connection.execute(
      text("SELECT id FROM users WHERE name = :name"),
      {"name": name},
    ).fetchone()
  return int(result[0]) if result else None


# ---------- Movies ----------

def get_movies(user_id: int) -> MovieData:
  """Retrieve all movies for a given user."""
  with engine.connect() as connection:
    result = connection.execute(text("""
      SELECT title, year, rating, poster
      FROM movies
      WHERE user_id = :user_id
    """), {"user_id": user_id})
    rows = result.fetchall()

  return {
    str(row[0]): {"year": int(row[1]), "rating": float(row[2]), "poster": str(row[3])}
    for row in rows
  }


def add_movie(user_id: int, title: str, year: int, rating: float, poster: str) -> None:
  """Add a new movie for a user."""
  try:
    with engine.begin() as connection:
      connection.execute(text("""
        INSERT INTO movies (user_id, title, year, rating, poster)
        VALUES (:user_id, :title, :year, :rating, :poster)
      """), {"user_id": user_id, "title": title, "year": year, "rating": rating, "poster": poster})
  except IntegrityError:
    raise ValueError("Film existiert bereits für diesen User.") from None


def delete_movie(user_id: int, title: str) -> None:
  """Delete a movie for a user."""
  with engine.begin() as connection:
    result = connection.execute(
      text("DELETE FROM movies WHERE user_id = :user_id AND title = :title"),
      {"user_id": user_id, "title": title},
    )
  if result.rowcount == 0:
    raise KeyError("Film nicht gefunden.")


def update_movie(user_id: int, title: str, rating: float) -> None:
  """Update rating for a user's movie."""
  with engine.begin() as connection:
    result = connection.execute(
      text("UPDATE movies SET rating = :rating WHERE user_id = :user_id AND title = :title"),
      {"user_id": user_id, "title": title, "rating": rating},
    )
  if result.rowcount == 0:
    raise KeyError("Film nicht gefunden.")
