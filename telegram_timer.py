import json
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import matplotlib.pyplot as plt
from io import BytesIO

LOG_FILE = "log.json"
user_start_times = {}

def format_duration(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

# Load existing logs
def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

# Save a new log entry
def save_log(entry):
    logs = load_logs()
    logs.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def generate_plot(user_id):
    logs = load_logs()
    sessions = []
    temp = {}

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        ts = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if ts.year == now.year and ts.month == now.month:
            if entry["action"] == "start":
                temp["start"] = ts
            elif entry["action"] == "end" and "start" in temp:
                duration = ts - temp["start"]
                sessions.append((temp["start"].date(), duration.total_seconds() / 60))  # minuti
                temp = {}

    if not sessions:
        return None  # niente da mostrare

    daily_totals = {}
    for date, minutes in sessions:
        daily_totals.setdefault(date, 0)
        daily_totals[date] += minutes

    dates = sorted(daily_totals.keys())
    durations = [daily_totals[d] for d in dates]

    plt.figure(figsize=(10, 6))
    plt.bar([d.strftime("%d %b") for d in dates], durations, color='skyblue')
    plt.xlabel("Date")
    plt.ylabel("Total duration (min)")
    plt.title("Total duration of this month's sessions")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf


# Get user stats for current month
def get_user_monthly_stats(user_id):
    logs = load_logs()
    sessions = []
    today_sessions = 0
    temp = {}

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        timestamp = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if timestamp.year == now.year and timestamp.month == now.month:
            if entry["action"] == "start":
                temp["start"] = timestamp
            elif entry["action"] == "end" and "start" in temp:
                duration = datetime.fromisoformat(entry["timestamp"]) - temp["start"]
                sessions.append(duration)
                temp = {}  # reset for next pair

        if timestamp.year == now.year and timestamp.month == now.month and timestamp.day == now.day and entry["action"] == "end":
            today_sessions += 1

    total_sessions = len(sessions)
    if total_sessions == 0:
        avg_duration = "N/A"
        max_duration = "N/A"
    else:
        avg_seconds = sum([s.total_seconds() for s in sessions]) / total_sessions
        avg_duration = str(round(avg_seconds // 60)) + " min"
        max_duration = str(round(max([s.total_seconds() for s in sessions]) // 60) ) + " min"

    return total_sessions, avg_duration, max_duration, today_sessions

# Get user stats for current year
def get_user_yearly_stats(user_id):
    logs = load_logs()
    sessions = []
    today_sessions = 0
    temp = {}

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        timestamp = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if timestamp.year == now.year:
            if entry["action"] == "start":
                temp["start"] = timestamp
            elif entry["action"] == "end" and "start" in temp:
                duration = datetime.fromisoformat(entry["timestamp"]) - temp["start"]
                sessions.append(duration)
                temp = {}  # reset for next pair

    total_sessions = len(sessions)
    if total_sessions == 0:
        avg_duration = "N/A"
        max_duration = "N/A"
    else:
        avg_seconds = sum([s.total_seconds() for s in sessions]) / total_sessions
        avg_duration = str(round(avg_seconds // 60)) + " min"
        max_duration = str(round(max([s.total_seconds() for s in sessions]) // 60) ) + " min"

    return total_sessions, avg_duration, max_duration

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    start_time = datetime.now().isoformat()

    user_start_times[user_id] = start_time

    save_log({
        "user_id": user_id,
        "username": username,
        "action": "start",
        "timestamp": start_time
    })

    await update.message.reply_text(f"Timer started for user {username}. Send /end to stop the session. Enjoy your session 😉")

# /end handler
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    end_time = datetime.now().isoformat()

    if user_id not in user_start_times:
        await update.message.reply_text("You need to start the timer first with /start.")
        return

    start_time_str = user_start_times.pop(user_id)
    start_time = datetime.fromisoformat(start_time_str)
    end_time_dt = datetime.fromisoformat(end_time)
    duration = end_time_dt - start_time
    formatted_duration = format_duration(duration)

    save_log({
        "user_id": user_id,
        "username": username,
        "action": "end",
        "timestamp": end_time,
        "duration": str(duration)
    })

    total_sessions_month, avg_duration_month, max_duration_month, today_sessions = get_user_monthly_stats(user_id)
    total_sessions_year, avg_duration_year, max_duration_year = get_user_yearly_stats(user_id)

    await update.message.reply_text(
        f"User: {username}\n"
        f"⏱ Session duration: {formatted_duration}\n"
        f"📅 Today's sessions: {today_sessions}\n"
    )

    await update.message.reply_text(
        "Month statistics\n"
        f"📅 Total sessions: {total_sessions_month}\n"
        f"📊 Average duration {avg_duration_month}\n"
        f"💪 Max duration: {max_duration_month}\n"
    )

    await update.message.reply_text(
        "Year statistics\n"
        f"📅 Total sessions: {total_sessions_year}\n"
        f"📊 Average duration {avg_duration_year}\n"
        f"💪 Max duration: {max_duration_year}\n"
    )

    plot_buf = generate_plot(user_id)
    if plot_buf:
        await update.message.reply_photo(photo=plot_buf, caption="📊 This month's sessions")


# Run the bot
if __name__ == '__main__':
    from settings import TOKEN

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("end", end))

    print("Bot is running...")
    app.run_polling()
