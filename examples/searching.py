"""Searching and listing upcoming cards.

`cards.upcoming()` and `cards.search()` both return `CardSummary` objects
rather than full `Card` objects. The summary carries enough to render a
list view (title, due date, project name, column title) but skips fields
like description, position, and timestamps. Fetch the full card with
`projects.list_cards()` if you need them.
"""

from __future__ import annotations

import sys

from craaft import CardSummary, CraaftClient


def show(card: CardSummary) -> None:
    bits = [card.title]
    if card.due_date:
        bits.append(f"due {card.due_date.date()}")
    if card.priority:
        bits.append(f"({card.priority})")
    print(f"  - {' '.join(bits)}  [{card.project_name} / {card.column_title}]")


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else "ship"

    with CraaftClient() as client:
        print("Upcoming cards (cards with a due date):")
        upcoming = client.cards.upcoming()
        if not upcoming:
            print("  (none)")
        for card in upcoming[:10]:
            show(card)

        print(f"\nSearch results for {query!r}:")
        results = client.cards.search(q=query, limit=10)
        if not results:
            print("  (no matches)")
        for card in results:
            show(card)


if __name__ == "__main__":
    main()
