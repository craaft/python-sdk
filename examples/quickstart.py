"""The shortest useful example.

Lists your projects, picks one, creates a card on it, and leaves a comment.
Cleans up the card and comment at the end so you can run it repeatedly.
"""

from __future__ import annotations

from craaft import CraaftClient


def main() -> None:
    # Token comes from the CRAAFT_API_TOKEN env var.
    with CraaftClient() as client:
        me = client.me.get()
        print(f"Signed in as {me.name} <{me.email}>")

        projects = client.projects.list()
        if not projects:
            print("No projects yet. Create one in the app first.")
            return

        project = projects[0]
        print(f"Using project: {project.name} ({project.total_cards} cards)")

        # Pick the first column on the board.
        full = client.projects.get(project.id)
        first_column = full.columns[0]

        card = client.projects.create_card(
            project.id,
            title="Hello from the Python SDK",
            column=first_column.key,
            position=0.0,
            description="Created by examples/quickstart.py",
        )
        print(f"Created card {card.id}: {card.title!r}")

        comment = client.cards.add_comment(card.id, body="First!")
        print(f"Added comment {comment.id}")

        # Clean up so this script is safe to re-run.
        client.comments.delete(comment.id)
        client.cards.delete(card.id)
        print("Cleaned up.")


if __name__ == "__main__":
    main()
