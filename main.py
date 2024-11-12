from datetime import datetime
from pymstodo import ToDoConnection
import dotenv
import os
import keyring
import argparse
from typing import Optional
import json
import os
from anthropic import Anthropic


def setup() -> None:
    """Initial setup and token storage"""
    client_id = os.getenv("MYDAYPLANNER_CLIENT")
    client_secret = os.getenv("MYDAYPLANNER_SECRET")

    auth_url = ToDoConnection.get_auth_url(client_id)
    redirect_resp = input(
        f"Go here and authorize:\n{auth_url}\n\nPaste the full redirect URL: "
    )
    token = ToDoConnection.get_token(client_id, client_secret, redirect_resp)

    keyring.set_password("mydayplanner", "microsoft_todo_token", str(token))
    print("Setup complete! Token saved.")


def mtdo_client() -> Optional[ToDoConnection]:
    """Get authenticated client or None if setup needed"""
    dotenv.load_dotenv()
    client_id = os.getenv("MYDAYPLANNER_CLIENT")
    client_secret = os.getenv("MYDAYPLANNER_SECRET")
    token_str = keyring.get_password("mydayplanner", "microsoft_todo_token")

    if not all([client_id, client_secret, token_str]):
        return None

    return ToDoConnection(
        client_id=client_id, client_secret=client_secret, token=eval(token_str)
    )


def fetch_tasks_from_lists(client, lists):
    """Fetch tasks from all lists and return them"""
    all_tasks = []

    for lst in lists:
        tasks = client.get_tasks(lst.list_id)
        if tasks:
            for task in tasks:
                all_tasks.append({"task": task.title, "list": lst.displayName})

    return all_tasks


def schedule(tasks, start_time, end_time):
    with open("instructions.md", "r") as f:
        instructions = f.read()

    anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""
        Based on these instructions:
        {instructions}

        And these tasks:
        {json.dumps(tasks, indent=2)}

        {f"And this start time: {start_time}" if start_time else ""}
        {f"And this end time: {end_time}" if end_time else ""}

        Generate a detailed schedule in simple json format and nothing else.
        The schedule should be optimized and include time estimates.

        Example output:
        {{
            "6:30am-7:30am": {{
            "activity": "Exercise - Push Day",
            "category": "fitness",
            "duration": 60
            }},
            "8:00am-9:30am": {{
            "activity": "Work Session 1: Review documentation (intellishelf)",
            "category": "work",
            "duration": 90,
            "notes": "Includes 17-minute break"
            }},
            ...
        }}
    """

    # Get Claude's response
    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    schedule = response.content[0].text

    print(schedule)


def main():
    parser = argparse.ArgumentParser(description="Microsoft Todo CLI")
    commands = ["setup", "lists", "tasks", "schedule"]
    parser.add_argument("command", choices=commands)
    parser.add_argument("--list-id", help="List ID for list-tasks command")
    parser.add_argument("--now", action="store_true", help="Use current time")
    parser.add_argument("--start", help="Start time for schedule command")
    parser.add_argument("--end", help="End time for schedule command")
    args = parser.parse_args()

    if args.command == "setup":
        setup()
        return

    client = mtdo_client()
    if not client:
        print("Please run setup first")
        return

    if args.command == "lists":
        lists = client.get_lists()
        print("\nAvailable Lists:")
        for lst in lists:
            print(lst)

    elif args.command == "tasks":
        lists = client.get_lists()
        all_tasks = fetch_tasks_from_lists(client, lists)

        for task_info in all_tasks:
            print(f"{task_info['list']}: {task_info['task']}")

    elif args.command == "schedule":
        start_time = args.start
        end_time = args.end
        if args.now:
            start_time = datetime.now().strftime("%I:%M%p")

        lists = client.get_lists()
        tasks = fetch_tasks_from_lists(client, lists)
        schedule(tasks, start_time, end_time)


if __name__ == "__main__":
    main()
