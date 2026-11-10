"""Local bootstrap only; production migrations follow in a later slice."""

from .database import Base, make_session_factory


def main() -> None:
    sessions = make_session_factory()
    Base.metadata.create_all(sessions.kw["bind"])


if __name__ == "__main__":
    main()
