# main.py

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from config import TELEGRAM_TOKEN
from logic import get_program_list, get_program_data, pretty_program_names
from openai_utils import ask_openai

SELECT_PROGRAM, Q_AND_A = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Клавиатура с программами
    programs = pretty_program_names()
    kb = [[name] for name in programs.values()]
    await update.message.reply_text(
        "Привет! Я ассистент по магистратурам ИТМО.\nВыбери интересующую программу:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_PROGRAM

async def select_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text.strip()
    programs = pretty_program_names()
    # Ищем slug по названию
    slug = None
    for s, name in programs.items():
        if name.lower() in user_choice.lower():
            slug = s
            break
    if not slug:
        await update.message.reply_text("Не удалось распознать программу. Попробуй снова.")
        return SELECT_PROGRAM

    context.user_data['program_slug'] = slug
    await update.message.reply_text(
        f"Выбрана программа: {programs[slug]}\nТеперь можешь задать любой вопрос по этой программе."
    )
    return Q_AND_A

async def qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text.strip()
    slug = context.user_data.get('program_slug')
    program_data = get_program_data(slug)
    if not program_data:
        await update.message.reply_text("Ошибка! Нет данных по выбранной программе. Начни с /start.")
        return SELECT_PROGRAM

    await update.message.reply_text("Готовлю ответ...")
    answer = ask_openai(question, program_data)
    await update.message.reply_text(answer)
    return Q_AND_A

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён. Напиши /start для нового запроса.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_PROGRAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_program)],
            Q_AND_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, qa)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
