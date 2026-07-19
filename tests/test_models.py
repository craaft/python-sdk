from datetime import date, datetime, timezone

from craaft.models import (
    Card,
    CardSummary,
    ChecklistItem,
    Column,
    Comment,
    Milestone,
    Project,
    User,
)


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
    assert u.avatar_url == "https://example.com/a.png"
    assert u.has_password is True


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
    assert c.key == "todo"
    assert c.position == 1.5


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
            "assignedUserName": "Bob",
            "size": 3,
            "priority": "high",
            "createdBy": "u1",
            "createdByName": "Alice",
            "updatedBy": "u1",
            "updatedByName": "Alice",
            "attachmentCount": 3,
            "checklistDone": 2,
            "checklistTotal": 5,
            "tags": ["api", "sdk"],
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T11:00:00+00:00",
        }
    )
    assert c.assigned_user_id == "u2"
    assert c.size == 3
    assert c.priority == "high"
    assert c.checklist_done == 2
    assert c.checklist_total == 5
    assert c.tags == ["api", "sdk"]
    assert c.due_date == datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_card_from_api_legacy_assignee_id_key():
    c = Card.from_api(
        {
            "id": "card1",
            "projectId": "proj1",
            "column": "todo",
            "title": "x",
            "position": 1.0,
            "assigneeId": "u2",
            "attachmentCount": 0,
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert c.assigned_user_id == "u2"
    # checklistDone / checklistTotal absent from the payload - safe default 0.
    assert c.checklist_done == 0
    assert c.checklist_total == 0


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
            "archived": True,
        }
    )
    assert c.archived is True
    assert c.description == "do it"


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
    assert c.body == "hi"


def test_checklist_item_from_api():
    i = ChecklistItem.from_api(
        {
            "id": "cl1",
            "cardId": "card1",
            "text": "write tests",
            "done": True,
            "position": 2.5,
            "createdAt": "2026-07-18T10:00:00Z",
            "updatedAt": "2026-07-18T11:00:00Z",
        }
    )
    assert i.card_id == "card1"
    assert i.text == "write tests"
    assert i.done is True
    assert i.position == 2.5
    assert i.created_at == datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)


def test_milestone_from_api():
    m = Milestone.from_api(
        {
            "id": "m1",
            "projectId": "p1",
            "name": "Beta launch",
            "dueOn": "2026-09-01",
            "achievedAt": "2026-08-30T09:00:00Z",
            "createdAt": "2026-07-18T10:00:00Z",
            "updatedAt": "2026-07-18T10:00:00Z",
        }
    )
    assert m.project_id == "p1"
    assert m.due_on == date(2026, 9, 1)
    assert m.achieved_at == datetime(2026, 8, 30, 9, 0, 0, tzinfo=timezone.utc)


def test_milestone_from_api_null_achieved_at():
    m = Milestone.from_api(
        {
            "id": "m1",
            "projectId": "p1",
            "name": "Beta launch",
            "dueOn": "2026-09-01",
            "achievedAt": None,
            "createdAt": "2026-07-18T10:00:00Z",
            "updatedAt": "2026-07-18T10:00:00Z",
        }
    )
    assert m.achieved_at is None


def test_project_from_api_with_columns():
    p = Project.from_api(
        {
            "id": "p1",
            "workspaceId": "w1",
            "workspaceName": "Personal",
            "name": "Demo",
            "description": "desc",
            "isFavorite": True,
            "publicToken": "tok",
            "backgroundImage": None,
            "backgroundColor": "#aabbcc",
            "colorScheme": None,
            "textColor": "dark",
            "myRole": "owner",
            "visibility": "private",
            "myBoardRole": "admin",
            "canUploadAttachments": True,
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
            "members": [{"id": "u1", "name": "Alice", "avatarUrl": ""}],
            "createdAt": "2026-05-08T10:00:00Z",
            "updatedAt": "2026-05-08T10:00:00Z",
        }
    )
    assert p.workspace_name == "Personal"
    assert p.background_color == "#aabbcc"
    assert p.visibility == "private"
    assert p.can_upload_attachments is True
    assert len(p.members) == 1
    assert p.members[0].name == "Alice"
