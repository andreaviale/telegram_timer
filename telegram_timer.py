import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import matplotlib.pyplot as plt
from io import BytesIO
from scipy import stats

LOG_FILE = "log.json"
user_start_times = {}

def format_duration(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}h {minutes:02}m {seconds:02}s"

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

def get_total_sessions(user_id):
    logs = load_logs()
    total_sessions = 0

    for entry in logs:
        if entry["user_id"] == user_id and entry["action"] == "end":
            total_sessions += 1

    return total_sessions

def generate_histogram_plot(user_id):
    logs = load_logs()
    sessions = []
    temp = {}

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        ts = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if (ts - now) < timedelta(days=30):
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
    plt.title("Total daily duration - last 30 days")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf

def generate_timeline_plot(user_id):
    from matplotlib.dates import DateFormatter
    import matplotlib.dates as mdates
    from collections import defaultdict

    logs = load_logs()
    sessions = []
    temp = {}

    # Raccogli tutte le sessioni utente degli ultimi 30 giorni
    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        ts = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if (ts-now) < timedelta(days=30):
            if entry["action"] == "start":
                temp["start"] = ts
            elif entry["action"] == "end" and "start" in temp:
                sessions.append((temp["start"], ts))
                temp = {}

    if not sessions:
        return None

    # Raggruppa per giorno
    daily_sessions = defaultdict(list)
    for start, end in sessions:
        day = start.date()
        daily_sessions[day].append((start, end))

    # Ordina i giorni
    sorted_days = sorted(daily_sessions.keys())
    y_labels = [day.strftime("%d %b") for day in sorted_days]
    y_pos = list(range(len(sorted_days)))

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, day in enumerate(sorted_days):
        # Weekend: sabato (5), domenica (6)
        if day.weekday() in [5, 6]:
            ax.axhspan(i - 0.5, i + 0.5, color="#f0f0f0")  # sfondo grigio chiaro

        for start, end in daily_sessions[day]:
            duration_minutes = (end - start).total_seconds() / 60
            start_minutes = start.hour * 60 + start.minute + start.second / 60

            # Colore in base alla durata
            if duration_minutes <= 20:
                color = "green"
            elif duration_minutes <= 30:
                color = "gold"
            else:
                color = "red"

            ax.barh(i, duration_minutes, left=start_minutes, height=0.4, color=color, edgecolor="black")

    # Etichette asse Y
    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels)
    ax.invert_yaxis()

    # Etichette asse X (orario)
    ax.set_xlim(0, 1440)  # 0 → 1440 minuti = 24 ore
    ax.set_xticks(range(0, 1441, 60))  # ogni ora
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25)],rotation=45)
    ax.set_xlabel("Time")
    ax.set_title("Consistency - last 30 days")

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf

def generate_gaussian_plot(user_id):
    import numpy as np
    from scipy.stats import norm

    logs = load_logs()
    durations = []
    temp = {}

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        ts = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if entry["action"] == "start":
            temp["start"] = ts
        elif entry["action"] == "end" and "start" in temp:
            duration = (ts - temp["start"]).total_seconds() / 60  # minuti
            durations.append(duration)
            temp = {}

    if not durations:
        return None

    # Calcolo statistico
    mean = np.mean(durations)
    std_dev = np.std(durations)

    # Prepara intervallo x
    x = np.linspace(min(durations), max(durations), 100)
    y = norm.pdf(x, mean, std_dev)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(durations, bins=50, density=True, alpha=0.6, color='skyblue', label='Real data')
    ax.plot(x, y, 'r-', label='Normal distribution')
    ax.axvline(mean, color='green', linestyle='--', label=f'Mean: {mean:.1f} min')
    ax.axvline(mean + std_dev, color='orange', linestyle=':', label=f'+1σ: {mean + std_dev:.1f} min')
    ax.axvline(mean - std_dev, color='orange', linestyle=':', label=f'-1σ: {mean - std_dev:.1f} min')
    shape, loc, scale = stats.lognorm.fit(durations)
    # Log-normal distribution
    ax.plot(x, stats.lognorm.pdf(x, shape, loc, scale), 'b--', label='Log-normal fit')

    ax.set_title("Session duration distribution (all data)")
    ax.set_xlabel("Session duration")
    ax.set_ylabel("Density")
    ax.legend()
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return buf

def get_user_daily_stats(user_id):
    logs = load_logs()
    sessions = []
    temp = {}
    total_duration = 0

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        timestamp = datetime.fromisoformat(entry["timestamp"])
        now = datetime.now()
        if timestamp.year == now.year and timestamp.month == now.month and timestamp.date() == now.date():
            if entry["action"] == "start":
                temp["start"] = timestamp
            elif entry["action"] == "end" and "start" in temp:
                duration = timestamp - temp["start"]
                sessions.append(duration)
                total_duration += duration.total_seconds()
                temp = {}  # reset for next pair

    total_sessions = len(sessions)
    if total_sessions == 0:
        avg_duration = "N/A"
        max_duration = "N/A"
        total_duration_formatted = "00:00:00"
    else:
        avg_seconds = sum([s.total_seconds() for s in sessions]) / total_sessions
        avg_duration = str(round(avg_seconds // 60)) + " min"
        max_duration = str(round(max([s.total_seconds() for s in sessions]) // 60) ) + " min"
        total_duration_formatted = format_duration(timedelta(seconds=total_duration))

    return total_sessions, avg_duration, max_duration, total_duration_formatted

# Get user stats for current month
def get_user_monthly_stats(user_id):
    logs = load_logs()
    sessions = []
    total_duration = 0
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
                total_duration += duration.total_seconds()
                temp = {}  # reset for next pair

    total_sessions = len(sessions)
    if total_sessions == 0:
        avg_duration = "N/A"
        max_duration = "N/A"
    else:
        avg_seconds = sum([s.total_seconds() for s in sessions]) / total_sessions
        avg_duration = str(round(avg_seconds // 60)) + " min"
        max_duration = str(round(max([s.total_seconds() for s in sessions]) // 60) ) + " min"
        total_duration_formatted = format_duration(timedelta(seconds=total_duration))

    return total_sessions, avg_duration, max_duration, total_duration_formatted

# Get user stats for current year
def get_user_yearly_stats(user_id):
    logs = load_logs()
    sessions = []
    total_duration = 0
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
                total_duration += duration.total_seconds()
                temp = {}  # reset for next pair

    total_sessions = len(sessions)
    if total_sessions == 0:
        avg_duration = "N/A"
        max_duration = "N/A"
    else:
        avg_seconds = sum([s.total_seconds() for s in sessions]) / total_sessions
        avg_duration = str(round(avg_seconds // 60)) + " min"
        max_duration = str(round(max([s.total_seconds() for s in sessions]) // 60) ) + " min"
        total_duration_formatted = format_duration(timedelta(seconds=total_duration))

    return total_sessions, avg_duration, max_duration, total_duration_formatted

def get_user_overall_stats(user_id):
    logs = load_logs()
    sessions = []
    total_duration = 0
    temp = {}

    for entry in logs:
        if entry["user_id"] != user_id:
            continue

        timestamp = datetime.fromisoformat(entry["timestamp"])
        if entry["action"] == "start":
            temp["start"] = timestamp
        elif entry["action"] == "end" and "start" in temp:
            duration = datetime.fromisoformat(entry["timestamp"]) - temp["start"]
            sessions.append(duration)
            total_duration += duration.total_seconds()
            temp = {}  # reset for next pair

    total_sessions = len(sessions)
    if total_sessions == 0:
        avg_duration = "N/A"
        max_duration = "N/A"
    else:
        avg_seconds = sum([s.total_seconds() for s in sessions]) / total_sessions
        avg_duration = str(round(avg_seconds // 60)) + " min"
        max_duration = str(round(max([s.total_seconds() for s in sessions]) // 60) ) + " min"
        total_duration_formatted = format_duration(timedelta(seconds=total_duration))

    return total_sessions, avg_duration, max_duration, total_duration_formatted

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

    session_count = get_total_sessions(user_id)
    session_type = "session" if session_count < 30 else "mission"

    await update.message.reply_text(f"Enjoy your {session_type} 😉")

# /end handler
async def end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    end_time = datetime.now().isoformat()

    if user_id not in user_start_times:
        await update.message.reply_text("You need to start the timer first with /start.")
        return

    duration = datetime.fromisoformat(end_time) - datetime.fromisoformat(user_start_times[user_id])
    formatted_duration = format_duration(duration)

    save_log({
        "user_id": user_id,
        "username": username,
        "action": "end",
        "timestamp": end_time,
        "duration": str(duration)
    })

    total_sessions = get_total_sessions(user_id)

    await update.message.reply_text(f"Session #{total_sessions} ended for user {username}. Duration: {formatted_duration}")

    total_sessions_day, avg_duration_day, max_duration_day, total_duration_day = get_user_daily_stats(user_id)
    total_sessions_month, avg_duration_month, max_duration_month, total_duration_month = get_user_monthly_stats(user_id)
    total_sessions_year, avg_duration_year, max_duration_year, total_duration_year = get_user_yearly_stats(user_id)
    total_sessions_overall, avg_duration_overall, max_duration_overall, total_duration_overall = get_user_overall_stats(user_id)

    await update.message.reply_text(
        "TODAY\n"
        f"📅 Total sessions: {total_sessions_day}\n"
        f"⏱ Total duration: {total_duration_day}\n"
        f"📊 Average duration {avg_duration_day}\n"
        f"💪 Max duration: {max_duration_day}\n"
        "THIS MONTH\n"
        f"📅 Total sessions: {total_sessions_month}\n"
        f"⏱ Total duration: {total_duration_month}\n"
        f"📊 Average duration {avg_duration_month}\n"
        f"💪 Max duration: {max_duration_month}\n"
        "THIS YEAR\n"
        f"📅 Total sessions: {total_sessions_year}\n"
        f"⏱ Total duration: {total_duration_year}\n"
        f"📊 Average duration {avg_duration_year}\n"
        f"💪 Max duration: {max_duration_year}\n"
        "OVERALL\n"
        f"📅 Total sessions: {total_sessions_overall}\n"
        f"⏱ Total duration: {total_duration_overall}\n"
        f"📊 Average duration {avg_duration_overall}\n"
        f"💪 Max duration: {max_duration_overall}\n"
    )

    plot_buf = generate_histogram_plot(user_id)
    if plot_buf:
        await update.message.reply_photo(photo=plot_buf, caption="Duration last 30 days")

    timeline_buf = generate_timeline_plot(user_id)
    if timeline_buf:
        await update.message.reply_photo(photo=timeline_buf, caption="🕒 Consistency last 30 days")

    gauss_buf = generate_gaussian_plot(user_id)
    if gauss_buf:
        await update.message.reply_photo(photo=gauss_buf, caption="📈 Duration distribution")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if args:
        username_arg = args[0].lstrip("@").lower()  # Rimuove @ e uniforma
    else:
        # Se nessun argomento: usa l'utente che invia il comando
        user = update.effective_user
        target_user_id = user.id
        username_arg = None

    if username_arg:
        # Cerca nei log l'user_id corrispondente al nome utente
        logs = load_logs()
        user_ids = {
            entry["username"].lower(): entry["user_id"]
            for entry in logs
            if "username" in entry
        }

        if username_arg not in user_ids:
            await update.message.reply_text(f"❌ Username @{username_arg} not found.")
            return

        target_user_id = user_ids[username_arg]

    await update.message.reply_text(f"📦 Report generation for @{username_arg if username_arg else update.effective_user.username}...")

    total_sessions_day, avg_duration_day, max_duration_day, total_duration_day = get_user_daily_stats(target_user_id)
    total_sessions_month, avg_duration_month, max_duration_month, total_duration_month = get_user_monthly_stats(target_user_id)
    total_sessions_year, avg_duration_year, max_duration_year, total_duration_year = get_user_yearly_stats(target_user_id)
    total_sessions_overall, avg_duration_overall, max_duration_overall, total_duration_overall = get_user_overall_stats(target_user_id)

    await update.message.reply_text(
        "**TODAY**\n"
        f"📅 Total sessions: {total_sessions_day}\n"
        f"⏱ Total duration: {total_duration_day}\n"
        f"📊 Average duration {avg_duration_day}\n"
        f"💪 Max duration: {max_duration_day}\n"
        "**THIS MONTH**\n"
        f"📅 Total sessions: {total_sessions_month}\n"
        f"⏱ Total duration: {total_duration_month}\n"
        f"📊 Average duration {avg_duration_month}\n"
        f"💪 Max duration: {max_duration_month}\n"
        "**THIS YEAR**\n"
        f"📅 Total sessions: {total_sessions_year}\n"
        f"⏱ Total duration: {total_duration_year}\n"
        f"📊 Average duration {avg_duration_year}\n"
        f"💪 Max duration: {max_duration_year}\n"
        "**OVERALL**\n"
        f"📅 Total sessions: {total_sessions_overall}\n"
        f"⏱ Total duration: {total_duration_overall}\n"
        f"📊 Average duration {avg_duration_overall}\n"
        f"💪 Max duration: {max_duration_overall}\n"
    )

    # 1. Istogramma durate giornaliere
    daily_plot = generate_histogram_plot(target_user_id)
    if daily_plot:
        await update.message.reply_photo(photo=daily_plot, caption="Duration last 30 days")

    # 2. Statistiche media/varianza
    stats_plot = generate_timeline_plot(target_user_id)
    if stats_plot:
        await update.message.reply_photo(photo=stats_plot, caption="📊 Consistency last 30 days")

    # 3. Campana di Gauss
    gauss_plot = generate_gaussian_plot(target_user_id)
    if gauss_plot:
        await update.message.reply_photo(photo=gauss_plot, caption="📈 Duration distribution")

    await update.message.reply_text("✅ Report completato.")

# Run the bot
if __name__ == '__main__':
    from settings import TOKEN

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("end", end))
    app.add_handler(CommandHandler("report", report))

    print("Bot is running...")
    app.run_polling()
