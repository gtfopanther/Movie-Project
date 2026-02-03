# movies.py
"""
movies.py - CLI movie database application.

Robustness requirements:
- No empty movie titles.
- For invalid user input, ask again instead of crashing.
- Use try/except to handle unexpected user inputs.
"""

from __future__ import annotations

import difflib
import random
import statistics
from typing import Optional

import movie_storage_sql as movie_storage
from movie_storage_sql import MovieData
import movie_api
import website_generator


def normalize(text: str) -> str:
  """Normalize text for case-insensitive comparisons."""
  return text.strip().lower()


def find_exact_key_case_insensitive(movies: MovieData, title: str) -> Optional[str]:
  """Find the real movie key ignoring case."""
  normalized_title = normalize(title)
  for key in movies:
    if normalize(key) == normalized_title:
      return key
  return None


def print_title() -> None:
  """Print application title."""
  print("*****Film Datenbank*****")


def print_menu() -> None:
  """Print menu options."""
  print("Menu:")
  print("0. Exit")
  print("1. Filme auflisten")
  print("2. Film hinzufügen")
  print("3. Film löschen")
  print("4. Film aktualisieren")
  print("5. Stats")
  print("6. Random Film")
  print("7. Film suchen")
  print("8. Filme sortieren nach rating")
  print("9. Generate website")
  print("10. rating histogram")



def ask_non_empty(prompt: str) -> str:
  """Ask until non-empty input is given."""
  while True:
    value = input(prompt).strip()
    if value:
      return value
    print("Eingabe darf nicht leer sein. Bitte nochmal.")


def ask_float(prompt: str) -> float:
  """Ask until a valid float is entered."""
  while True:
    raw_value = input(prompt).strip()
    try:
      return float(raw_value)
    except ValueError:
      print("Ungültige Zahl. Bitte nochmal.")


def ask_int(prompt: str) -> int:
  """Ask until a valid integer is entered."""
  while True:
    raw_value = input(prompt).strip()
    try:
      return int(raw_value)
    except ValueError:
      print("Ungültige Zahl. Bitte nochmal.")


def ask_choice(prompt: str, valid_choices: set[str]) -> str:
  """Ask until a valid menu choice is entered."""
  while True:
    choice = input(prompt).strip()
    if choice in valid_choices:
      return choice
    print("Ungültige Auswahl. Bitte nochmal.")


def list_movies() -> None:
  """List all movies."""
  movies = movie_storage.get_movies()
  print(f"{len(movies)} movies total")
  for title, data in movies.items():
    print(f"{title} ({data['year']}): {data['rating']}")


def add_movie() -> None:
  """Add a new movie using OMDb API (title only)."""
  movies = movie_storage.get_movies()

  title = ask_non_empty("film name eingeben: ")
  if find_exact_key_case_insensitive(movies, title):
    print("Film existiert bereits.")
    return

  try:
    fetched = movie_api.fetch_movie_from_omdb(title)
  except movie_api.MovieNotFoundError:
    print("Film nicht gefunden. Bitte prüfe den Titel.")
    return
  except movie_api.ApiConnectionError:
    print("API ist aktuell nicht erreichbar. Bitte später erneut versuchen.")
    return

  movie_storage.add_movie(
    fetched["title"],
    fetched["year"],
    fetched["rating"],
    fetched["poster"],
  )

  print(
    f"\"{fetched['title']}\" ({fetched['year']}) "
    f"mit Rating {fetched['rating']} hinzugefügt."
  )




def delete_movie() -> None:
  """Delete an existing movie (robust against invalid input)."""
  movies = movie_storage.get_movies()

  while True:
    title = ask_non_empty("film name: ")
    existing = find_exact_key_case_insensitive(movies, title)
    if existing:
      movie_storage.delete_movie(existing)
      print(f'"{existing}" gelöscht.')
      return
    print("Film existiert nicht. Bitte nochmal.")


def update_movie() -> None:
  """Update movie rating (robust against invalid input)."""
  while True:
    movies = movie_storage.get_movies()

    title = ask_non_empty("filmname: ")
    existing = find_exact_key_case_insensitive(movies, title)
    if not existing:
      print("Film existiert nicht. Bitte nochmal.")
      continue

    rating = ask_float("neues rating: ")
    movie_storage.update_movie(existing, rating)
    print(f'"{existing}" aktualisiert.')
    return


def compute_stats(movies: MovieData) -> Optional[dict[str, float | list[str]]]:
  """Compute rating statistics."""
  if not movies:
    return None

  ratings = [data["rating"] for data in movies.values()]
  max_rating = max(ratings)
  min_rating = min(ratings)

  return {
    "avg": sum(ratings) / len(ratings),
    "median": statistics.median(ratings),
    "max": max_rating,
    "min": min_rating,
    "best": [t for t, d in movies.items() if d["rating"] == max_rating],
    "worst": [t for t, d in movies.items() if d["rating"] == min_rating],
  }


def stats() -> None:
  """Display statistics."""
  movies = movie_storage.get_movies()
  result = compute_stats(movies)

  if not result:
    print("keine filme in datenbank")
    return

  print(f"average rating: {result['avg']:.2f}")
  print(f"median rating: {result['median']:.2f}")
  print(f"bester film ({result['max']}):")
  for title in result["best"]:
    print(f"- {title}")
  print(f"schlechtester film ({result['min']}):")
  for title in result["worst"]:
    print(f"- {title}")


def random_movie() -> None:
  """Print a random movie."""
  movies = movie_storage.get_movies()
  if not movies:
    print("keine filme in datenbank")
    return

  title = random.choice(list(movies))
  data = movies[title]
  print(f"{title} ({data['year']}): {data['rating']}")


def search_movie() -> None:
  """Search for movies by title."""
  movies = movie_storage.get_movies()

  query = ask_non_empty("filmname: ")
  normalized_query = normalize(query)

  matches = [
    (t, d) for t, d in movies.items()
    if normalized_query in normalize(t)
  ]

  if matches:
    for title, data in matches:
      print(f"{title} ({data['year']}): {data['rating']}")
    return

  suggestions = difflib.get_close_matches(query, movies.keys(), n=5, cutoff=0.6)
  print("Film nicht gefunden.")
  if suggestions:
    print("Meinst du:")
    for suggestion in suggestions:
      print(suggestion)


def movies_sorted_by_rating() -> None:
  """List movies sorted by rating."""
  movies = movie_storage.get_movies()
  if not movies:
    print("keine filme in datenbank")
    return

  for title, data in sorted(
    movies.items(),
    key=lambda item: item[1]["rating"],
    reverse=True,
  ):
    print(f"{title} ({data['year']}): {data['rating']}")


def rating_histogram() -> None:
  """Save a histogram of ratings to a file."""
  movies = movie_storage.get_movies()
  if not movies:
    print("keine filme in datenbank")
    return

  filename = ask_non_empty("dateiname um histogram zu speichern: ")

  try:
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel
  except ImportError:
    print("matplotlib is not available.")
    return

  ratings = [data["rating"] for data in movies.values()]

  try:
    plt.figure()
    plt.hist(ratings, bins=10)
    plt.title("film rating Histogram")
    plt.xlabel("rating")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"Histogram gespeichert zu {filename}")
  except OSError as error:
    print(f"konnte histogram nicht speichern: {error}")


def main() -> None:
  """Run the CLI loop."""
  print_title()
  valid_choices = {str(i) for i in range(11)}


  while True:
    print_menu()
    choice = ask_choice("wähle (0-9): ", valid_choices)
    print()

    if choice == "1":
      list_movies()
    elif choice == "2":
      add_movie()
    elif choice == "3":
      delete_movie()
    elif choice == "4":
      update_movie()
    elif choice == "5":
      stats()
    elif choice == "6":
      random_movie()
    elif choice == "7":
      search_movie()
    elif choice == "8":
      movies_sorted_by_rating()
    elif choice == "9":
      movies = movie_storage.get_movies()
      website_generator.generate_website(movies, app_title="Film Datenbank")
      print("Website was generated successfully.")
    elif choice == "10":
      rating_histogram()
    elif choice == "0":
      print("Bye!")
      break

    print()


if __name__ == "__main__":
  main()
