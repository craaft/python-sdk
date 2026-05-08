# Examples

Runnable scripts that show how to use the SDK against a real Craaft API.

Set your token first:

```bash
export CRAAFT_API_TOKEN=cra_...
# optional: point at a local server
export CRAAFT_BASE_URL=http://localhost:8080/api/v1
```

Then run any example:

```bash
python examples/quickstart.py
```

| File | What it shows |
|------|---------------|
| `quickstart.py` | The shortest path to do something useful: list projects, create a card, leave a comment. |
| `card_lifecycle.py` | The full flow for a card: create, set priority/size/due date via PATCH, comment, delete. |
| `error_handling.py` | Which exceptions to catch and how to read the fields they carry. |
| `retries.py` | Tuning `RetryConfig` and reacting to `RateLimitError`. |
| `searching.py` | `cards.search()` and `cards.upcoming()`, both of which return `CardSummary`. |
| `advanced_client.py` | Custom session, debug logging, and pointing the client at a different base URL. |

Each script is self-contained and prints what it did, so you can read along while it runs. None of them write any data they don't clean up themselves.
