# main.py
"""
main.py - CLI movie database application.

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

from storage import movie_storage_sql as movie_storage
from storage.movie_storage_sql import MovieData

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
  print("10. Switch user")
  print("11. rating histogram")


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


def select_or_create_user() -> tuple[int, str]:
  """Let the user select an existing profile or create a new one."""
  while True:
    users = movie_storage.list_users()
    print("Select a user:")
    for idx, (_, name) in enumerate(users, start=1):
      print(f"{idx}. {name}")
    print(f"{len(users) + 1}. Create new user")

    choice = ask_int("Enter choice: ")

    if 1 <= choice <= len(users):
      user_id, name = users[choice - 1]
      print(f"Welcome back, {name}! 🎬")
      return user_id, name

    if choice == len(users) + 1:
      new_name = ask_non_empty("New user name: ")
      try:
        user_id = movie_storage.create_user(new_name)
      except ValueError:
        print("User existiert bereits. Bitte anderen Namen wählen.")
        continue
      print(f"User '{new_name}' erstellt. 🎬")
      return user_id, new_name

    print("Ungültige Auswahl. Bitte nochmal.")


def list_movies(user_id: int, user_name: str) -> None:
  """List all movies for the active user."""
  movies = movie_storage.get_movies(user_id)
  if not movies:
    print(f"📢 {user_name}, deine Filmsammlung ist leer. Füge Filme hinzu!")
    return

  print(f"{len(movies)} movies total")
  for title, data in movies.items():
    print(f"{title} ({data['year']}): {data['rating']}")


def add_movie(user_id: int) -> None:
  """Add a movie for the active user (title only; API + fallback)."""
  movies = movie_storage.get_movies(user_id)

  title = ask_non_empty("film name eingeben: ")
  if find_exact_key_case_insensitive(movies, title):
    print("Film existiert bereits.")
    return

  try:
    fetched = movie_api.fetch_movie_from_omdb(title)
    movie_storage.add_movie(
      user_id,
      fetched["title"],
      fetched["year"],
      fetched["rating"],
      fetched["poster"],
    )
    print(f"✅ \"{fetched['title']}\" added successfully.")
    return

  except movie_api.MovieNotFoundError:
    print("Film nicht gefunden. Bitte prüfe den Titel.")
    return

  except movie_api.ApiConnectionError:
    print("API ist aktuell nicht erreichbar. Manuelle Eingabe wird verwendet.")
    year = ask_int("erscheinungsjahr: ")
    rating = ask_float("film rating 1-10: ")
    poster = ""
    movie_storage.add_movie(user_id, title, year, rating, poster)
    print(f"✅ \"{title}\" manuell hinzugefügt.")
    return


def delete_movie(user_id: int) -> None:
  """Delete a movie for the active user."""
  while True:
    movies = movie_storage.get_movies(user_id)

    title = ask_non_empty("film name: ")
    existing = find_exact_key_case_insensitive(movies, title)
    if existing:
      movie_storage.delete_movie(user_id, existing)
      print(f"\"{existing}\" gelöscht.")
      return
    print("Film existiert nicht. Bitte nochmal.")


def update_movie(user_id: int) -> None:
  """Update a movie rating for the active user."""
  while True:
    movies = movie_storage.get_movies(user_id)

    title = ask_non_empty("filmname: ")
    existing = find_exact_key_case_insensitive(movies, title)
    if not existing:
      print("Film existiert nicht. Bitte nochmal.")
      continue

    rating = ask_float("neues rating: ")
    movie_storage.update_movie(user_id, existing, rating)
    print(f"\"{existing}\" aktualisiert.")
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


def stats(user_id: int, user_name: str) -> None:
  """Display statistics for the active user."""
  movies = movie_storage.get_movies(user_id)
  result = compute_stats(movies)

  if not result:
    print(f"📢 {user_name}, keine filme in deiner datenbank.")
    return

  print(f"average rating: {result['avg']:.2f}")
  print(f"median rating: {result['median']:.2f}")
  print(f"bester film ({result['max']}):")
  for title in result["best"]:
    print(f"- {title}")
  print(f"schlechtester film ({result['min']}):")
  for title in result["worst"]:
    print(f"- {title}")


def random_movie(user_id: int) -> None:
  """Print a random movie for the active user."""
  movies = movie_storage.get_movies(user_id)
  if not movies:
    print("keine filme in datenbank")
    return

  title = random.choice(list(movies))
  data = movies[title]
  print(f"{title} ({data['year']}): {data['rating']}")


def search_movie(user_id: int) -> None:
  """Search for movies by title for the active user."""
  movies = movie_storage.get_movies(user_id)

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


def movies_sorted_by_rating(user_id: int) -> None:
  """List movies sorted by rating for the active user."""
  movies = movie_storage.get_movies(user_id)
  if not movies:
    print("keine filme in datenbank")
    return

  for title, data in sorted(
    movies.items(),
    key=lambda item: item[1]["rating"],
    reverse=True,
  ):
    print(f"{title} ({data['year']}): {data['rating']}")


def rating_histogram(user_id: int) -> None:
  """Save a histogram of ratings to a file for the active user."""
  movies = movie_storage.get_movies(user_id)
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
  valid_choices = {str(i) for i in range(12)}
  user_id, user_name = select_or_create_user()

  while True:
    print_menu()
    choice = ask_choice("wähle (0-11): ", valid_choices)
    print()

    if choice == "1":
      list_movies(user_id, user_name)
    elif choice == "2":
      add_movie(user_id)
    elif choice == "3":
      delete_movie(user_id)
    elif choice == "4":
      update_movie(user_id)
    elif choice == "5":
      stats(user_id, user_name)
    elif choice == "6":
      random_movie(user_id)
    elif choice == "7":
      search_movie(user_id)
    elif choice == "8":
      movies_sorted_by_rating(user_id)
    elif choice == "9":
      movies = movie_storage.get_movies(user_id)
      filename = f"{user_name}.html"
      website_generator.generate_website(
        movies,
        app_title=f"{user_name}'s Movie App",
        filename=filename,
      )
      print("Website was generated successfully.")
    elif choice == "10":
      user_id, user_name = select_or_create_user()
    elif choice == "11":
      rating_histogram(user_id)
    elif choice == "0":
      print("Bye!")
      break

    print()


if __name__ == "__main__":
  main()
