"""Searching and listing upcoming cards.

`cards.upcoming()` returns `UpcomingCard` objects and `cards.search()`
returns `SearchResult` objects - lightweight previews rather than full
`Card` objects, each carrying only the fields their endpoint actually
populates (an upcoming card has a due date but no description; a search hit
has a description snippet but no due date). Fetch the full card with
`projects.list_cards()` if you need everything.
"""

from __future__ import annotations

import sys

from craaft import CraaftClient, SearchResult, UpcomingCard


def show(card: SearchResult | UpcomingCard) -> None:
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
