"""
website_generator.py - Generate a static website from the movie database.

Reads template from: _static/index_template.html
Writes output to:    _static/<filename>.html
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from storage.movie_storage_sql import MovieData


STATIC_DIR = Path("_static")
TEMPLATE_PATH = STATIC_DIR / "index_template.html"


def _movie_li_html(title: str, year: int, rating: float, poster: str) -> str:
  safe_title = escape(title)
  safe_year = escape(str(year))

  if poster:
    safe_poster = escape(poster)
    poster_html = f'<img class="movie-poster" src="{safe_poster}" alt="{safe_title} poster" />'
  else:
    poster_html = (
      '<div class="movie-poster" style="display:flex;align-items:center;justify-content:center;">'
      'No poster</div>'
    )

  return f"""
<li>
  <div class="movie">
    {poster_html}
    <div class="movie-title">{safe_title}</div>
    <div class="movie-year">{safe_year}</div>
  </div>
</li>
""".strip()


def generate_website(movies: MovieData, app_title: str, filename: str) -> None:
  if not TEMPLATE_PATH.exists():
    raise FileNotFoundError(f"Template nicht gefunden: {TEMPLATE_PATH}")

  template = TEMPLATE_PATH.read_text(encoding="utf-8")

  sorted_items = sorted(movies.items(), key=lambda item: item[1]["rating"], reverse=True)
  grid_html = "\n".join(
    _movie_li_html(
      title=title,
      year=int(data["year"]),
      rating=float(data["rating"]),
      poster=str(data.get("poster", "")),
    )
    for title, data in sorted_items
  )

  result_html = template.replace("__TEMPLATE_TITLE__", escape(app_title))
  result_html = result_html.replace("__TEMPLATE_MOVIE_GRID__", grid_html)

  output_path = STATIC_DIR / filename
  output_path.write_text(result_html, encoding="utf-8")
