"""
movie_storage_sql.py - SQLite storage using SQLAlchemy (raw SQL via text()).

Public API:
- get_movies() -> dict
- add_movie(title, year, rating, poster)
- delete_movie(title)
- update_movie(title, rating)

Movie dict shape:
{
  "Inception": {"year": 2010, "rating": 8.8, "poster": "https://...jpg"},
  ...
}
"""

from __future__ import annotations

from typing import Dict, TypedDict

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
  """Create movies table if it does not exist (with poster column)."""
  with engine.begin() as connection:
    connection.execute(text("""
      CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE NOT NULL,
        year INTEGER NOT NULL,
        rating REAL NOT NULL,
        poster TEXT NOT NULL
      )
    """))


_init_db()


def get_movies() -> MovieData:
  """Retrieve all movies from the database."""
  with engine.connect() as connection:
    result = connection.execute(text("SELECT title, year, rating, poster FROM movies"))
    rows = result.fetchall()

  return {
    row[0]: {"year": int(row[1]), "rating": float(row[2]), "poster": str(row[3])}
    for row in rows
  }


def add_movie(title: str, year: int, rating: float, poster: str) -> None:
  """Add a new movie to the database."""
  try:
    with engine.begin() as connection:
      connection.execute(
        text("""
          INSERT INTO movies (title, year, rating, poster)
          VALUES (:title, :year, :rating, :poster)
        """),
        {"title": title, "year": year, "rating": rating, "poster": poster},
      )
  except IntegrityError:
    raise ValueError(f"Movie '{title}' exists already.") from None


def delete_movie(title: str) -> None:
  """Delete a movie from the database."""
  with engine.begin() as connection:
    result = connection.execute(
      text("DELETE FROM movies WHERE title = :title"),
      {"title": title},
    )

  if result.rowcount == 0:
    raise KeyError(f"Movie '{title}' not found.")


def update_movie(title: str, rating: float) -> None:
  """Update a movie's rating in the database."""
  with engine.begin() as connection:
    result = connection.execute(
      text("UPDATE movies SET rating = :rating WHERE title = :title"),
      {"title": title, "rating": rating},
    )

  if result.rowcount == 0:
    raise KeyError(f"Movie '{title}' not found.")
