from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timedelta
import re
import math

from db.models import User, Activity, DailyGoal, WeightLog, get_session, init_db
from utils.config import (
    BOT_TOKEN, POINTS_RUN, POINTS_GYM, POINTS_STUDY_PER_HOUR,
    STREAK_BRONZE, STREAK_SILVER, STREAK_GOLD
)


# ============ HELPERS ============

def get_or_create_user(telegram_id: int, name: str = None) -> User:
    session = get_session()
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
    # Don't close session - keep user attached
    return user


def calculate_points(activity_type: str, duration_mins: int = 0) -> int:
    if activity_type == "run":
        return POINTS_RUN
    elif activity_type == "gym":
        return POINTS_GYM
    elif activity_type == "study":
        hours = duration_mins / 60
        return int(hours * POINTS_STUDY_PER_HOUR)
    return 0


def get_streak_emoji(days: int) -> str:
    if days >= STREAK_GOLD:
        return "🟡 GOLD"
    elif days >= STREAK_SILVER:
        return "⚪ SILVER"
    elif days >= STREAK_BRONZE:
        return "🟤 BRONZE"
    return "🔥"


def format_weight_progress(user: User) -> str:
    if not user.current_weight:
        return "No weight logged yet. Use /weight to log."
    
    diff = user.current_weight - user.weight_goal
    direction = "to go" if diff > 0 else "under goal!"
    
    return f"📊 {user.current_weight}kg → {user.weight_goal}kg ({abs(diff):.1f}kg {direction})"


# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id, update.effective_user.first_name)
    
    await update.message.reply_text(
        f"👋 Hey {user.name or 'there'}! Welcome to FocusTrack!\n\n"
        "I'll help you stay focused on your goals.\n\n"
        "Quick start:\n"
        "• /intent - Set today's goals\n"
        "• /run 5 - Log a run\n"
        "• /gym 45 - Log gym\n"
        "• /study r 30 - Study R for 30 mins\n"
        "• /study quant 60 - Study quant for 1 hour\n"
        "• /weight 92.5 - Log your weight\n"
        "• /stats - See your progress\n"
        "• /whatnow - What should I do next?\n\n"
        "Let's get moving! 💪"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n\n"
        "• /start - Welcome message\n"
        "• /intent - Set today's focus\n"
        "• /run [km] - Log a run\n"
        "• /gym [mins] - Log gym session\n"
        "• /study [subject] [mins] - Log study time\n"
        "• /weight [kg] - Log weight\n"
        "• /stats - Your progress\n"
        "• /whatnow - Get a suggestion\n"
        "• /settings - Customize your bot\n\n"
        "Examples:\n"
        "`/run 5`\n"
        "`/gym 45`\n"
        "`/study r 30`\n"
        "`/weight 92.5`",
        parse_mode="Markdown"
    )


async def log_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    
    # Parse: /run 5 or /run 5km
    text = update.message.text.replace("/run", "").strip()
    match = re.match(r"(\d+\.?\d*)", text)
    
    if not match:
        await update.message.reply_text("Usage: /run [km]\nExample: /run 5")
        return
    
    km = float(match.group(1))
    points = POINTS_RUN
    
    # Log activity
    session = get_session()
    user_obj = session.query(User).filter(User.telegram_id == user.telegram_id).first()
    
    activity = Activity(
        user_id=user.telegram_id,
        activity_type="run",
        activity_name="run",
        distance_km=km,
        points_earned=points
    )
    session.add(activity)
    
    user_obj.total_points += points
    user_obj.calculate_level()
    session.commit()
    
    # Store values before closing
    level = user_obj.level
    total_points = user_obj.total_points
    session.close()
    
    await update.message.reply_text(
        f"🏃 *Run logged!*\n"
        f"Distance: {km}km\n"
        f"Points: +{points}\n"
        f"Level: {level} ({total_points} total)",
        parse_mode="Markdown"
    )


async def log_gym(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    
    # Parse: /gym 45 or /gym chest 45
    text = update.message.text.replace("/gym", "").strip()
    
    # Try to find number at end
    parts = text.split()
    if parts and parts[-1].isdigit():
        mins = int(parts[-1])
        name = " ".join(parts[:-1]) if len(parts) > 1 else "gym"
    elif parts and parts[0].isdigit():
        mins = int(parts[0])
        name = "gym"
    else:
        await update.message.reply_text("Usage: /gym [name] [mins]\nExample: /gym chest 45")
        return
    
    points = POINTS_GYM
    
    session = get_session()
    user_obj = session.query(User).filter(User.telegram_id == user.telegram_id).first()
    
    activity = Activity(
        user_id=user.telegram_id,
        activity_type="gym",
        activity_name=name,
        duration_mins=mins,
        points_earned=points
    )
    session.add(activity)
    
    user_obj.total_points += points
    user_obj.calculate_level()
    session.commit()
    
    level = user_obj.level
    session.close()
    
    await update.message.reply_text(
        f"💪 *Gym logged!*\n"
        f"Session: {name} ({mins} min)\n"
        f"Points: +{points}\n"
        f"Level: {level}",
        parse_mode="Markdown"
    )


async def log_study(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    
    # Parse: /study r 30 or /study quant 60
    text = update.message.text.replace("/study", "").strip()
    parts = text.split()
    
    if len(parts) < 2:
        await update.message.reply_text("Usage: /study [subject] [mins]\nExample: /study r 30")
        return
    
    subject = parts[0]
    mins = int(parts[1])
    points = calculate_points("study", mins)
    
    session = get_session()
    user_obj = session.query(User).filter(User.telegram_id == user.telegram_id).first()
    
    activity = Activity(
        user_id=user.telegram_id,
        activity_type="study",
        activity_name=subject,
        duration_mins=mins,
        points_earned=points
    )
    session.add(activity)
    
    user_obj.total_points += points
    user_obj.calculate_level()
    session.commit()
    
    level = user_obj.level
    session.close()
    
    await update.message.reply_text(
        f"📚 *Study logged!*\n"
        f"Subject: {subject}\n"
        f"Time: {mins} min\n"
        f"Points: +{points}\n"
        f"Level: {level}",
        parse_mode="Markdown"
    )


async def log_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    
    text = update.message.text.replace("/weight", "").strip()
    match = re.match(r"(\d+\.?\d*)", text)
    
    if not match:
        await update.message.reply_text("Usage: /weight [kg]\nExample: /weight 92.5")
        return
    
    weight = float(match.group(1))
    
    session = get_session()
    
    # Get user from THIS session
    user_obj = session.query(User).filter(User.telegram_id == user.telegram_id).first()
    
    log = WeightLog(user_id=user.telegram_id, weight=weight)
    session.add(log)
    
    user_obj.current_weight = weight
    session.commit()
    
    # Store values before closing
    current_weight = weight
    weight_goal = user_obj.weight_goal
    session.close()
    
    diff = current_weight - weight_goal
    direction = "to go" if diff > 0 else "under goal!"
    
    await update.message.reply_text(
        f"⚖️ *Weight logged!*\n"
        f"Current: {current_weight}kg\n"
        f"Goal: {weight_goal}kg\n\n"
        f"📊 {current_weight}kg → {weight_goal}kg ({abs(diff):.1f}kg {direction})",
        parse_mode="Markdown"
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_or_create_user(update.effective_user.id)
    
    session = get_session()
    
    # Get recent activities
    activities = session.query(Activity).filter(
        Activity.user_id == user.telegram_id
    ).order_by(Activity.logged_at.desc()).limit(10).all()
    
    # Get weight logs
    weight_logs = session.query(WeightLog).filter(
        WeightLog.user_id == user.telegram_id
    ).order_by(WeightLog.logged_at.desc()).limit(5).all()
    
    # Store values before closing session
    level = user.level
    total_points = user.total_points
    current_weight = user.current_weight or 'Not set'
    weight_goal = user.weight_goal
    session.close()
    
    # Build message
    msg = f"📊 *Your Stats*\n\n"
    msg += f"🎯 Level: {level}\n"
    msg += f"⭐ Total Points: {total_points}\n"
    msg += f"⚖️ Current Weight: {current_weight}kg\n"
    msg += f"🏁 Goal: {weight_goal}kg\n\n"
    
    if activities:
        msg += "📝 *Recent Activity:*\n"
        for a in activities[:5]:
            time = a.logged_at.strftime("%m/%d")
            if a.activity_type == "run":
                msg += f"• {time} 🏃 {a.distance_km}km (+{a.points_earned})\n"
            elif a.activity_type == "gym":
                msg += f"• {time} 💪 {a.activity_name} {a.duration_mins}m (+{a.points_earned})\n"
            elif a.activity_type == "study":
                msg += f"• {time} 📚 {a.activity_name} {a.duration_mins}m (+{a.points_earned})\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def whatnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suggest the best next task based on incomplete goals"""
    user = get_or_create_user(update.effective_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    session = get_session()
    goal = session.query(DailyGoal).filter(
        DailyGoal.user_id == user.telegram_id,
        DailyGoal.date == today
    ).first()
    
    # Store values before closing
    exercise_completed = goal.exercise_completed if goal else None
    study_completed = goal.study_completed if goal else None
    session.close()
    
    suggestions = []
    
    if goal:
        if not exercise_completed:
            suggestions.append("🏃 Log your exercise (run/gym)")
        if not study_completed:
            suggestions.append("📚 Study session")
    
    if not suggestions:
        suggestions = [
            "🏃 Go for a run",
            "💪 Hit the gym",
            "📚 Study R or quant",
            "⚖️ Log your weight"
        ]
    
    import random
    suggestion = random.choice(suggestions)
    
    await update.message.reply_text(
        f"🤔 *What now?*\n\n"
        f"{suggestion}\n\n"
        f"Or log it directly:\n"
        f"`/run 5` / `/gym 45` / `/study r 30`",
        parse_mode="Markdown"
    )


async def set_intent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set today's focus goals"""
    user = get_or_create_user(update.effective_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    text = update.message.text.replace("/intent", "").strip()
    
    if not text:
        await update.message.reply_text(
            "🎯 *Set Today's Focus*\n\n"
            "Usage: /intent [study], [exercise]\n\n"
            "Examples:\n"
            "/intent R, 30min run\n"
            "/intent quant, gym\n"
            "/intent R, quant",
            parse_mode="Markdown"
        )
        return
    
    session = get_session()
    goal = session.query(DailyGoal).filter(
        DailyGoal.user_id == user.telegram_id,
        DailyGoal.date == today
    ).first()
    
    if not goal:
        goal = DailyGoal(user_id=user.telegram_id, date=today)
        session.add(goal)
    
    # Parse simple format
    parts = [p.strip() for p in text.split(",")]
    if len(parts) >= 1:
        goal.study_goal = parts[0]
    if len(parts) >= 2:
        goal.exercise_goal = parts[1]
    
    session.commit()
    
    # Store values before closing session
    study = goal.study_goal or 'None'
    exercise = goal.exercise_goal or 'None'
    session.close()
    
    await update.message.reply_text(
        f"✅ *Today's Focus Set!*\n\n"
        f"📚 Study: {study}\n"
        f"🏃 Exercise: {exercise}\n\n"
        f"Complete them and log with /run, /gym, /study",
        parse_mode="Markdown"
    )


async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set weight goal"""
    user = get_or_create_user(update.effective_user.id)
    
    text = update.message.text.replace("/goal", "").strip()
    match = re.match(r"(\d+\.?\d*)", text)
    
    if not match:
        await update.message.reply_text("Usage: /goal [kg]\nExample: /goal 85")
        return
    
    goal = float(match.group(1))
    
    session = get_session()
    user_obj = session.query(User).filter(User.telegram_id == user.telegram_id).first()
    user_obj.weight_goal = goal
    session.commit()
    session.close()
    
    await update.message.reply_text(
        f"🎯 *Weight goal set!*\n"
        f"Goal: {goal}kg",
        parse_mode="Markdown"
    )


async def weekly_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show weekly summary"""
    user = get_or_create_user(update.effective_user.id)
    
    session = get_session()
    
    # Get this week's activities
    week_ago = datetime.now() - timedelta(days=7)
    activities = session.query(Activity).filter(
        Activity.user_id == user.telegram_id,
        Activity.logged_at >= week_ago
    ).all()
    
    # Count by type
    runs = sum(1 for a in activities if a.activity_type == "run")
    gym = sum(1 for a in activities if a.activity_type == "gym")
    study = sum(a.duration_mins or 0 for a in activities if a.activity_type == "study")
    
    # Weight change
    weight_logs = session.query(WeightLog).filter(
        WeightLog.user_id == user.telegram_id,
        WeightLog.logged_at >= week_ago
    ).order_by(WeightLog.logged_at).all()
    
    # Store values before closing
    if weight_logs:
        first_weight = weight_logs[0].weight
        last_weight = weight_logs[-1].weight
        weight_change = last_weight - first_weight
        weight_msg = f"{first_weight} → {last_weight}kg ({weight_change:+.1f})"
    else:
        weight_msg = "No weigh-ins"
    session.close()
    
    await update.message.reply_text(
        f"📅 *Weekly Review*\n\n"
        f"🏃 Runs: {runs}\n"
        f"💪 Gym: {gym}\n"
        f"📚 Study: {study} min\n"
        f"⚖️ Weight: {weight_msg}\n\n"
        f"⭐ Points this week: {sum(a.points_earned for a in activities)}",
        parse_mode="Markdown"
    )


# ============ ERROR HANDLER ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    print(f"Error: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "⚠️ Oops! Something went wrong. Please try again."
        )


# ============ MAIN ============

def run_bot():
    # Initialize DB
    init_db()
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("run", log_run))
    app.add_handler(CommandHandler("gym", log_gym))
    app.add_handler(CommandHandler("study", log_study))
    app.add_handler(CommandHandler("weight", log_weight))
    app.add_handler(CommandHandler("goal", set_goal))
    app.add_handler(CommandHandler("stats", show_stats))
    app.add_handler(CommandHandler("whatnow", whatnow))
    app.add_handler(CommandHandler("intent", set_intent))
    app.add_handler(CommandHandler("weekly", weekly_review))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    print("🤖 Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()