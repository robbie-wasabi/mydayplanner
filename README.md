# MyDayPlanner

CLI tool that integrates with Microsoft Todo to generate optimized daily schedules using Claude AI.

## Features
- Fetches tasks from Microsoft Todo lists
- Generates smart schedules based on task context and personal preferences
- Respects work/life balance and daily routines
- Handles time blocks and breaks automatically

## Setup
1. Create Microsoft Todo API credentials: https://github.com/inbalboa/pymstodo/blob/master/GET_KEY.md
2. Set environment variables:
```bash
MYDAYPLANNER_CLIENT=your_client_id
MYDAYPLANNER_SECRET=your_client_secret
ANTHROPIC_API_KEY=your_claude_api_key
```
3. Run initial setup:
```bash
python main.py setup
```
4. Add instructions.md file to root directory and fill in with your personal preferences where indicated [ex: ...]

## Usage
```bash
# List all todo lists
python main.py lists

# Show all tasks
python main.py tasks

# Generate schedule
python main.py schedule [--now] [--start TIME] [--end TIME]
```

## Example Schedule Output
```json
{
  "6:30am-7:30am": {
    "activity": "Exercise - Push Day",
    "category": "fitness",
    "duration": 60
  },
  "8:00am-9:30am": {
    "activity": "Work Session 1",
    "category": "work", 
    "duration": 90,
    "notes": "Includes 17-minute break"
  }
}
```
