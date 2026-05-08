from datetime import datetime, timezone

from craaft.models import Card, CardSummary, Column, Comment, Project, User


def test_user_from_api():
    u = User.from_api(
        {
            "id": "u1",
            "email": "a@b.co",
            "name": "Alice",
            "username": "alice",
            "avatarUrl": "https://example.com/a.png",
            "hasPassword": True,
        }
    )
    assert u.id == "u1"
    assert u.email == "a@b.co"
    assert u.name == "Alice"
    assert u.username == "alice"
    assert u.avatar_url == "https://example.com/a.png"
    assert u.has_password is True


def test_user_tolerates_extra_keys():
    u = User.from_api(
        {
            "id": "u1",
            "email": "a@b.co",
            "name": "A",
            "username": "a",
            "avatarUrl": None,
            "hasPassword": False,
            "futureField": "ignored",
        }
    )
    assert u.id == "u1"


def test_column_from_api():
    c = Column.from_api(
        {
            "id": "col1",
            "key": "todo",
            "title": "To Do",
            "color": "#aaa",
            "position": 1.5,
            "isDone": False,
            "cardLimit": None,
        }
    )
    assert c.id == "col1"
    assert c.key == "todo"
    assert c.title == "To Do"
    assert c.color == "#aaa"
    assert c.position == 1.5
    assert c.is_done is False
    assert c.card_limit is None


def test_card_from_api_full():
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "Do thing",
            "position": 2.0,
            "description": "do it",
            "dueDate": "2026-06-01T00:00:00+00:00",
            "assignedUserId": "u2",
            "size": "m",
            "priority": "high",
            "createdBy": "u1",
            "attachmentCount": 3,
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T11:00:00+00:00",
        }
    )
    assert c.id == "card1"
    assert c.project_id == "proj1"
    assert c.due_date == datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert c.assigned_user_id == "u2"
    assert c.size == "m"
    assert c.priority == "high"
    assert c.created_by == "u1"
    assert c.attachment_count == 3
    assert c.created_at == datetime(2026, 5, 8, 10, 0, 0, tzinfo=timezone.utc)
    assert c.updated_at == datetime(2026, 5, 8, 11, 0, 0, tzinfo=timezone.utc)


def test_card_from_api_legacy_assignee_id_key():
    # Older spec used assigneeId; we still accept it for forward/back compat.
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "x",
            "position": 1.0,
            "description": None,
            "dueDate": None,
            "assigneeId": "u2",
            "size": None,
            "priority": None,
            "createdBy": None,
            "attachmentCount": 0,
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.assigned_user_id == "u2"


def test_card_from_api_nullables():
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "Do thing",
            "position": 2.0,
            "description": None,
            "dueDate": None,
            "assignedUserId": None,
            "size": None,
            "priority": None,
            "createdBy": None,
            "attachmentCount": 0,
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.description is None
    assert c.due_date is None
    assert c.size is None


def test_card_summary_from_upcoming_shape():
    c = CardSummary.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "projectName": "Launch board",
            "columnKey": "doing",
            "columnTitle": "In Progress",
            "title": "Ship the migration",
            "dueDate": "2026-05-05T00:00:00+02:00",
            "assignedUserId": "u1",
            "priority": "high",
        }
    )
    assert c.id == "card1"
    assert c.project_name == "Launch board"
    assert c.column_key == "doing"
    assert c.column_title == "In Progress"
    assert c.due_date is not None
    assert c.due_date.year == 2026
    assert c.assigned_user_id == "u1"
    assert c.priority == "high"
    assert c.description is None


def test_card_summary_from_search_shape():
    c = CardSummary.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "projectName": "Launch board",
            "columnKey": "doing",
            "columnTitle": "In Progress",
            "title": "Ship",
            "description": "do it",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.description == "do it"
    assert c.updated_at == datetime(2026, 5, 8, 10, 0, 0, tzinfo=timezone.utc)
    assert c.due_date is None
    assert c.priority is None


def test_comment_from_api():
    c = Comment.from_api(
        {
            "id": "cm1",
            "cardId": "card1",
            "authorId": "u1",
            "body": "hi",
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.card_id == "card1"
    assert c.author_id == "u1"
    assert c.body == "hi"


def test_project_from_api_with_columns():
    p = Project.from_api(
        {
            "id": "p1",
            "workspaceId": "w1",
            "name": "Demo",
            "description": "desc",
            "isFavorite": True,
            "publicToken": "tok",
            "customCss": None,
            "backgroundImage": None,
            "colorScheme": None,
            "textColor": "dark",
            "totalCards": 5,
            "columnCounts": {"todo": 2, "doing": 3},
            "columns": [
                {
                    "id": "c1",
                    "key": "todo",
                    "title": "To Do",
                    "color": "#aaa",
                    "position": 1.0,
                    "isDone": False,
                    "cardLimit": None,
                }
            ],
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert p.workspace_id == "w1"
    assert p.is_favorite is True
    assert p.public_token == "tok"
    assert p.text_color == "dark"
    assert p.total_cards == 5
    assert p.column_counts == {"todo": 2, "doing": 3}
    assert len(p.columns) == 1
    assert p.columns[0].title == "To Do"


def test_project_from_api_minimal_no_columns_array():
    # /projects list endpoints might omit nested columns array
    p = Project.from_api(
        {
            "id": "p1",
            "workspaceId": "w1",
            "name": "Demo",
            "description": None,
            "isFavorite": False,
            "publicToken": None,
            "customCss": None,
            "backgroundImage": None,
            "colorScheme": None,
            "textColor": "light",
            "totalCards": 0,
            "columnCounts": {},
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert p.columns == []
