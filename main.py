from datetime import datetime
import hashlib
from pymstodo import ToDoConnection
import dotenv
import os
import keyring
import argparse
from typing import Optional
import json
import os
from anthropic import Anthropic
from appdirs import user_cache_dir

model = "claude-3-5-sonnet-20241022"


def setup(client_id, client_secret) -> None:
    """Initial setup and token storage"""

    auth_url = ToDoConnection.get_auth_url(client_id)
    redirect_resp = input(
        f"Go here and authorize:\n{auth_url}\n\nPaste the full redirect URL: "
    )
    token = ToDoConnection.get_token(client_id, client_secret, redirect_resp)

    keyring.set_password("mydayplanner", "microsoft_todo_token", str(token))
    print("Setup complete! Token saved.")


def mtdo_client(client_id, client_secret) -> Optional[ToDoConnection]:
    """Get authenticated client or None if setup needed"""
    dotenv.load_dotenv()
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


def schedule(tasks, prev_schedule, instructions, date, start_time, end_time):

    anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""
        Based on these instructions:
        {instructions}

        And these tasks:
        {json.dumps(tasks, indent=2)}

        {f"And today's date: {date.strftime('%Y-%m-%d')}" if date else ""}
        {f"And today's weekday: {date.strftime('%A')}" if date else ""}

        {f"And this start time: {start_time}" if start_time else ""}
        {f"And this end time: {end_time}" if end_time else ""}

        And this previous schedule:
        {json.dumps(prev_schedule, indent=2)} if prev_schedule else ""

        Generate a detailed schedule in simple json format and nothing else.
        The schedule should be optimized and include time estimates.

        NOTE:
        If a previous schedule is provided and tasks have changed, update the schedule accordingly.

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
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "prompt": prompt,
        "instructions_hash": hashlib.sha256(instructions.encode()).hexdigest(),
        "timestamp": int(datetime.now().timestamp()),
        "schedule": response.content[0].text,
    }


def main():
    parser = argparse.ArgumentParser(description="Microsoft Todo CLI")
    commands = ["setup", "lists", "tasks", "schedule"]
    parser.add_argument("command", choices=commands)
    parser.add_argument("--list-id", help="List ID for list-tasks command")
    parser.add_argument("--now", action="store_true", help="Use current time")
    parser.add_argument("--start", help="Start time for schedule command")
    parser.add_argument("--end", help="End time for schedule command")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start with a fresh schedule, ignoring previous ones",
    )
    args = parser.parse_args()

    with open("instructions.md", "r") as f:
        instructions = f.read()

    client_id = os.getenv("MYDAYPLANNER_CLIENT")
    if not client_id:
        print("MYDAYPLANNER_CLIENT is not set")
        return
    client_secret = os.getenv("MYDAYPLANNER_SECRET")
    if not client_secret:
        print("MYDAYPLANNER_SECRET is not set")
        return

    if args.command == "setup":
        setup(client_id, client_secret)
        return

    client = mtdo_client(client_id, client_secret)
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
        fresh = args.fresh
        if args.now:
            start_time = datetime.now().strftime("%I:%M%p")

        date = datetime.now()
        cache_dir = user_cache_dir("mydayplanner")

        prev_schedule = None
        if not fresh:
            schedules = [f for f in os.listdir(cache_dir) if f.startswith("schedule_")]
            if schedules:
                newest_file = max(
                    schedules,
                    key=lambda x: os.path.getctime(os.path.join(cache_dir, x)),
                )
                schedule_path = os.path.join(cache_dir, newest_file)

                try:
                    with open(schedule_path) as f:
                        existing_schedule = json.load(f)
                        if (
                            datetime.fromtimestamp(
                                existing_schedule["timestamp"]
                            ).date()
                            == date.date()
                        ):
                            prev_schedule = existing_schedule
                            print(f"Loaded today's schedule from {schedule_path}")
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass

        lists = client.get_lists()
        print(f"Fetched {len(lists)} lists")

        tasks = fetch_tasks_from_lists(client, lists)
        print(f"Fetched {len(tasks)} tasks")

        print("Scheduling...")
        schedule_json = schedule(
            tasks, prev_schedule, instructions, date, start_time, end_time
        )

        cache_dir = user_cache_dir("mydayplanner")
        timestamp = int(datetime.now().timestamp())
        output_path = os.path.join(cache_dir, f"schedule_{timestamp}.json")

        os.makedirs(cache_dir, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(schedule_json, f, indent=2)

        print(f"Schedule saved to {output_path}")
        print(schedule_json["schedule"])


if __name__ == "__main__":
    main()
