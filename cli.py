from __future__ import annotations

import argparse
import sys

from book_sync.config import load_settings
from book_sync.pipeline import list_books, run_process, run_rss


def cmd_rss(args: argparse.Namespace) -> None:
    settings = load_settings()
    run_rss(args.url, settings)


def cmd_list(args: argparse.Namespace) -> None:
    books = list_books()
    if not books:
        print("No books found")
        return
    for title, stage in books:
        print(f"{title} – {stage}")


def cmd_process(args: argparse.Namespace) -> None:
    settings = load_settings()
    run_process(args.title, settings)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="transcribe",
        description="Convert Audiobookshelf RSS feeds into timestamped transcripts",
    )
    sub = parser.add_subparsers(dest="command")

    rss_p = sub.add_parser("rss", help="Add and process an RSS feed")
    rss_p.add_argument("url", help="Audiobookshelf RSS feed URL")
    rss_p.set_defaults(func=cmd_rss)

    list_p = sub.add_parser("list", help="List all books and their status")
    list_p.set_defaults(func=cmd_list)

    proc_p = sub.add_parser("process", help="Resume processing for a book")
    proc_p.add_argument("title", help="Book title (as shown by list)")
    proc_p.set_defaults(func=cmd_process)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
