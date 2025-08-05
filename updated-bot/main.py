from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from config import TELEGRAM_TOKEN
from logic import get_program_list, get_program_data, pretty_program_names
from openai_utils import ask_openai

SELECT_TOPIC, SELECT_PROGRAM, Q_AND_A = range(3)

BACK_BTN = "⬅️ Назад"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["Спросить о программе"], ["Спросить о выборе дисциплин"]]
    await update.message.reply_text(
        "Привет! Я ассистент по магистратурам ИТМО.\nЧто тебя интересует?",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    # Сброс стейта
    context.user_data.clear()
    return SELECT_TOPIC

async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text.strip().lower()
    if user_choice == BACK_BTN.lower():
        return await start(update, context)
    if "программ" in user_choice:
        context.user_data['question_type'] = 'about'
    elif "дисциплин" in user_choice:
        context.user_data['question_type'] = 'disciplines'
    else:
        await update.message.reply_text("Пожалуйста, выбери одну из опций.")
        return SELECT_TOPIC

    # Клавиатура с программами + назад
    programs = pretty_program_names()
    kb = [[name] for name in programs.values()]
    kb.append([BACK_BTN])
    await update.message.reply_text(
        "Выбери программу:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_PROGRAM

async def select_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text.strip()
    if user_choice == BACK_BTN:
        return await start(update, context)
    programs = pretty_program_names()
    slug = None
    for s, name in programs.items():
        if name.lower() in user_choice.lower():
            slug = s
            break
    if not slug:
        await update.message.reply_text("Не удалось распознать программу. Попробуй снова.")
        return SELECT_PROGRAM

    context.user_data['program_slug'] = slug
    # Добавляем кнопку "Назад" на этом этапе тоже
    kb = [[BACK_BTN]]
    if context.user_data.get('question_type') == 'about':
        await update.message.reply_text(
            f"Выбрана программа: {programs[slug]}\nВведи свой вопрос о программе.",
            reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            f"Выбрана программа: {programs[slug]}\nВведи свой вопрос о дисциплинах (например, 'Какие элективы выбрать?').",
            reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        )
    return Q_AND_A

async def qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text.strip()
    if question == BACK_BTN:
        # Возвращаемся к выбору программы, но не сбрасываем вопрос типа
        programs = pretty_program_names()
        kb = [[name] for name in programs.values()]
        kb.append([BACK_BTN])
        await update.message.reply_text(
            "Выбери программу:",
            reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
        )
        return SELECT_PROGRAM

    slug = context.user_data.get('program_slug')
    question_type = context.user_data.get('question_type')
    program_data = get_program_data(slug)
    if not program_data:
        await update.message.reply_text("Ошибка! Нет данных по выбранной программе. Начни с /start.")
        return SELECT_PROGRAM

    # Формируем только нужные поля для экономии токенов
    if question_type == 'about':
        data = {
            "title": program_data["title"],
            "institute": program_data["institute"],
            "meta": program_data["meta"],
            "about": program_data["about"],
            "career": program_data["career"],
            "admission": program_data["admission"],
            "faq": program_data["faq"]
        }
    else:  # disciplines
        data = {
            "title": program_data["title"],
            "meta": program_data["meta"],
            "curriculum_disciplines": program_data["curriculum_disciplines"]
        }

    await update.message.reply_text("Готовлю ответ...")
    answer = ask_openai(question, data)
    await update.message.reply_text(answer)
    # Не выходим из Q_AND_A, пользователь может задать еще вопросы или вернуться назад
    return Q_AND_A

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён. Напиши /start для нового запроса.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_topic)],
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
