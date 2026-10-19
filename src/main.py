import logging
import logging.handlers
import os
import re
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv

from bot import enchiridion_run

base_path = Path(__file__).resolve().parent
env_path = base_path.parent / ".env"
load_dotenv(dotenv_path=env_path)

DEV = True

LOG_DIR = base_path.parent / "logs"

# Folders that don't count as "project code" when looking for the origin module
IGNORED_DIRS = {"site-packages", "dist-packages", "venv", ".venv", "env", "__pycache__"}


class ModuleErrorHandler(logging.Handler):
    """Writes each error to logs/errors/<module>.log, based on the module it originated from."""

    def __init__(
        self,
        directory,
        project_root,
        formatter,
        level=logging.ERROR,
        max_bytes=5 * 1024 * 1024,
        backup_count=3,
    ):
        super().__init__(level)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.project_root = Path(project_root).resolve()
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.setFormatter(formatter)
        self._handlers: dict[str, logging.Handler] = {}

    def _origin_module(self, record: logging.LogRecord) -> str:
        # Find the last traceback frame that lives inside the project
        if record.exc_info and record.exc_info[2]:
            found = None
            tb = record.exc_info[2]
            while tb:
                filename = Path(tb.tb_frame.f_code.co_filename).resolve()
                try:
                    rel = filename.relative_to(self.project_root)
                except ValueError:
                    pass  # frame from an external library / stdlib
                else:
                    if not IGNORED_DIRS.intersection(rel.parts):
                        found = ".".join(rel.with_suffix("").parts)
                tb = tb.tb_next
            if found:
                return found
        # No traceback (or no project frame): fall back to the logger name
        return record.name

    def _get_handler(self, name: str) -> logging.Handler:
        handler = self._handlers.get(name)
        if handler is None:
            handler = logging.handlers.RotatingFileHandler(
                self.directory / f"{name}.log",
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(self.formatter)
            self._handlers[name] = handler
        return handler

    def emit(self, record: logging.LogRecord) -> None:
        try:
            name = re.sub(r"[^\w.\-]", "_", self._origin_module(record)) or "unknown"
            self._get_handler(name).handle(record)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        for handler in self._handlers.values():
            handler.close()
        self._handlers.clear()
        super().close()


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if DEV else logging.INFO)

    # All logs (rotates at midnight, keeps 14 days)
    all_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "bot.log",
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    all_handler.setLevel(logging.DEBUG if DEV else logging.INFO)
    all_handler.setFormatter(formatter)

    # Errors (ERROR and CRITICAL) split by originating module
    error_handler = ModuleErrorHandler(
        directory=LOG_DIR / "errors",
        project_root=base_path,
        formatter=formatter,
        level=logging.ERROR,
    )

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if DEV else logging.INFO)
    console_handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(all_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)

    # Reduce noise from chatty libraries
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    # Unhandled exceptions in the main thread
    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("uncaught").critical(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = handle_exception

    # Unhandled exceptions in other threads
    def handle_thread_exception(args):
        logging.getLogger("uncaught.thread").critical(
            f"Unhandled exception in thread {args.thread.name if args.thread else '?'}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = handle_thread_exception


if __name__ == "__main__":
    setup_logging()
    log = logging.getLogger("main")

    token = os.getenv("DEV_TOKEN") if DEV else os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("Token not found in .env (DEV=%s)", DEV)
        sys.exit(1)

    try:
        log.info("Starting bot (%s mode)", "DEV" if DEV else "PRODUCTION")
        enchiridion_run(token)
    except KeyboardInterrupt:
        log.info("Bot stopped manually")
    except Exception:
        log.exception("Bot crashed with a fatal error")
        raise