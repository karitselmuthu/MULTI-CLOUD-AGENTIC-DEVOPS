"""Apply versioned PostgreSQL metadata migrations."""

from data.postgres import migrate
from .database import make_session_factory


def main() -> None:
    sessions = make_session_factory()
    migrate(sessions.kw["bind"])


if __name__ == "__main__":
    main()
