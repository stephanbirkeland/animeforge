"""AnimeForge - Lo-fi Girl-style interactive anime scene engine."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("animeforge")
except PackageNotFoundError:
    __version__ = "unknown"
