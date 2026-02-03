"""
movie_api.py - Fetch movie info from OMDb API.

Hardcoded API key (no .env).
Fetches: Title, Year, imdbRating, Poster
Includes error handling via exceptions.
"""

from __future__ import annotations

from typing import TypedDict

import requests


OMDB_API_KEY = "fcf6b17a"


class ApiConnectionError(Exception):
  """Raised when OMDb cannot be reached or request fails."""


class MovieNotFoundError(Exception):
  """Raised when OMDb returns no result for the requested title."""


class FetchedMovie(TypedDict):
  title: str
  year: int
  rating: float
  poster: str


def fetch_movie_from_omdb(title: str) -> FetchedMovie:
  """Fetch movie info from OMDb by title. Raises on errors."""
  try:
    response = requests.get(
      "https://www.omdbapi.com/",
      params={"apikey": OMDB_API_KEY, "t": title},
      timeout=10,
    )
    response.raise_for_status()
    data = response.json()
  except (requests.RequestException, ValueError) as error:
    raise ApiConnectionError("OMDb API nicht erreichbar oder ungültige Antwort.") from error

  if data.get("Response") != "True":
    raise MovieNotFoundError("Film nicht gefunden (OMDb).")

  fetched_title = str(data.get("Title", "")).strip()
  year_raw = str(data.get("Year", "")).strip()
  rating_raw = str(data.get("imdbRating", "")).strip()
  poster_raw = str(data.get("Poster", "")).strip()

  # Year can be like "2010" or "2010–2014" (series) -> take first 4 chars
  try:
    year = int(year_raw[:4])
  except (ValueError, TypeError) as error:
    raise MovieNotFoundError("Ungültiges Jahr von OMDb erhalten.") from error

  # imdbRating can be "N/A"
  try:
    rating = float(rating_raw)
  except (ValueError, TypeError) as error:
    raise MovieNotFoundError("Kein gültiges Rating von OMDb erhalten.") from error

  # Poster can be "N/A"
  poster = "" if poster_raw in ("N/A", "None") else poster_raw

  if not fetched_title:
    fetched_title = title

  return {"title": fetched_title, "year": year, "rating": rating, "poster": poster}
