"""The full flow for a card.

The Craaft API accepts most card fields on PATCH, so the practical pattern
is: create with the basics, then update to set priority, size, and due
date. This script walks through that flow, adds a comment, and deletes
everything at the end.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from craaft import CraaftClient


def main() -> None:
    with CraaftClient() as client:
        projects = client.projects.list()
        if not projects:
            print("Create a project in the app first.")
            return
        project = client.projects.get(projects[0].id)
        column = project.columns[0]

        # Step 1: create with the bare essentials.
        card = client.projects.create_card(
            project.id,
            title="Migrate the billing service",
            column=column.key,
            position=0.0,
            description="Part of the Q3 reliability work.",
        )
        print(f"Created card {card.id}")

        # Step 2: set priority and a due date a week out. PATCH is where
        # these stick reliably (POST drops them on some server builds).
        due = datetime.now(timezone.utc) + timedelta(days=7)
        card = client.cards.update(
            card.id,
            priority="high",
            due_date=due,
        )
        print(f"  priority={card.priority} due={card.due_date}")

        # Step 3: leave a comment, then edit it.
        comment = client.cards.add_comment(card.id, body="Kicking this off")
        print(f"Posted comment {comment.id}")

        comment = client.comments.update(comment.id, body="Kicking this off today")
        print(f"  edited: {comment.body!r}")

        # Step 4: move the card to the next column (if there is one).
        if len(project.columns) > 1:
            next_col = project.columns[1]
            card = client.cards.update(card.id, column=next_col.key, position=0.0)
            print(f"Moved card to {next_col.title!r}")

        # Cleanup.
        client.comments.delete(comment.id)
        client.cards.delete(card.id)
        print("Cleaned up.")


if __name__ == "__main__":
    main()
