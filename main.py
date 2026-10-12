import asyncio
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from dotenv import load_dotenv
from database import init_db, save_task, get_tasks, complete_task
from database import delete_task
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_stats


load_dotenv(Path(__file__).with_name(".env"))

dp = Dispatcher()
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить задачу")],
        [
            KeyboardButton(text="📋 Мои задачи"),
            KeyboardButton(text="📊 Статистика")
        ],
        [KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

def task_keyboard(task_id: int, done: bool):
    buttons = []

    if not done:
        buttons.append(
            InlineKeyboardButton(
                text="✅ Выполнить",
                callback_data=f"done:{task_id}"
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete:{task_id}"
        )
    )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])
class TaskForm(StatesGroup):
    title = State()
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я TaskMate 📋\n"
        "Помогу тебе вести задачи.\n\n"
        "Используй кнопки меню или напиши /help.",
        reply_markup=menu
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📋 Как пользоваться TaskMate\n\n"
        "➕ Добавить задачу — включить ввод задач. "
        "Отправляй каждую задачу отдельным сообщением.\n\n"
        "📋 Мои задачи — открыть список и закончить ввод.\n"
        "✅ Выполнить — отметить задачу выполненной.\n"
        "🗑 Удалить — удалить задачу.\n"
        "📊 Статистика — посмотреть количество задач.\n\n"
        "Команды:\n"
        "/start — главное меню и выход из ввода\n"
        "/help — помощь\n"
        "/add текст — добавить одну задачу\n"
        "/list — список задач\n"
        "/done номер — выполнить задачу\n"
        "/delete номер — удалить задачу\n"
        "/stats — статистика и выход из ввода\n"
        "/cancel — закончить ввод задач",
        reply_markup=menu
    )


@dp.message(Command("add"))
async def add_task(message: Message):
    if message.from_user is None:
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Напиши задачу после команды:\n"
            "/add Сделать домашку"
        )
        return

    title = parts[1].strip()

    if len(title) > 200:
        await message.answer("Сократи задачу до 200 символов.")
        return

    user_id = message.from_user.id
    save_task(user_id, title)
    await message.answer(f"✅ Задача добавлена: {title}")


@dp.message(Command("list"))
async def list_tasks(message: Message):
    if message.from_user is None:
        return

    user_tasks = get_tasks(message.from_user.id)

    if not user_tasks:
        await message.answer(
            "Задач пока нет.\n"
            "Нажми «➕ Добавить задачу»."
        )
        return

    await message.answer("📋 Твои задачи:")

    for task_id, title, done in user_tasks:
        status = "✅" if done else "⬜"

        await message.answer(
            f"{task_id}. {status} {title}",
            reply_markup=task_keyboard(task_id, done)
        )

@dp.message(Command("done"))
async def done_command(message: Message):
    if message.from_user is None:
        return

    parts = (message.text or "").split()

    if len(parts) != 2:
        await message.answer("Укажи номер задачи: /done 1")
        return

    try:
        task_id = int(parts[1])
    except ValueError:
        await message.answer("Номер задачи должен быть целым числом.")
        return

    if not 1 <= task_id <= 9223372036854775807:
        await message.answer("Укажи корректный номер из /list.")
        return

    changed = complete_task(message.from_user.id, task_id)

    if changed:
        await message.answer(f"✅ Задача №{task_id} выполнена!")
    else:
        await message.answer(
            "Задача не найдена или уже выполнена.\n"
            "Посмотри номера через /list."
        )
@dp.message(Command("delete"))
async def delete_command(message: Message):
    if message.from_user is None:
        return

    parts = (message.text or "").split()

    if len(parts) != 2:
        await message.answer("Укажи номер задачи: /delete 1")
        return

    try:
        task_id = int(parts[1])
    except ValueError:
        await message.answer("Номер задачи должен быть целым числом.")
        return

    if not 1 <= task_id <= 9223372036854775807:
        await message.answer("Укажи корректный номер из /list.")
        return

    deleted = delete_task(message.from_user.id, task_id)

    if deleted:
        await message.answer(f"🗑 Задача №{task_id} удалена.")
    else:
        await message.answer("Задача не найдена. Проверь номер через /list.")
@dp.message(F.text == "📋 Мои задачи")
async def tasks_button(message: Message, state: FSMContext):
    await state.clear()
    await list_tasks(message)


@dp.message(F.text == "❓ Помощь")
async def help_button(message: Message, state: FSMContext):
    await state.clear()
    await help_command(message)
@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ввод задачи отменён.", reply_markup=menu)


@dp.message(F.text == "➕ Добавить задачу")
async def add_button(message: Message, state: FSMContext):
    await state.set_state(TaskForm.title)
    await message.answer(
        "Напиши текст новой задачи одним сообщением.\n"
        "Для отмены — /cancel."
    )

@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def stats_command(message: Message, state: FSMContext):
    await state.clear()

    if message.from_user is None:
        return

    total, completed, active = get_stats(message.from_user.id)

    await message.answer(
        "📊 Твоя статистика\n\n"
        f"📋 Всего задач: {total}\n"
        f"✅ Выполнено: {completed}\n"
        f"⬜ Осталось: {active}",
        reply_markup=menu
    )
@dp.message(TaskForm.title, F.text)
async def receive_task(message: Message, state: FSMContext):
    if message.from_user is None:
        return

    title = message.text.strip()

    if title.startswith("/"):
        await message.answer("Отправь текст задачи или /cancel.")
        return

    if not 1 <= len(title) <= 200:
        await message.answer("Текст задачи должен содержать от 1 до 200 символов.")
        return

    save_task(message.from_user.id, title)

    await message.answer(
        f"✅ Задача добавлена: {title}\n\n"
        "Можешь отправить следующую задачу.\n"
        "Чтобы закончить, нажми «📋 Мои задачи» "
        "или отправь /cancel.",
        reply_markup=menu
    )
@dp.callback_query(F.data.startswith("done:"))
async def done_callback(callback: CallbackQuery):
    if not isinstance(callback.message, Message):
        await callback.answer("Открой список задач заново.")
        return

    try:
        task_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный номер задачи.")
        return

    if not 1 <= task_id <= 9223372036854775807:
        await callback.answer("Некорректный номер задачи.")
        return

    user_id = callback.from_user.id
    user_tasks = get_tasks(user_id)

    task = next(
        (item for item in user_tasks if item[0] == task_id),
        None
    )

    if task is None:
        await callback.answer("Задача не найдена.")
        return

    if task[2]:
        await callback.answer("Задача уже выполнена.")
        return

    changed = complete_task(user_id, task_id)

    if not changed:
        await callback.answer("Задача не найдена или уже выполнена.")
        return

    await callback.answer("Задача выполнена ✅")

    await callback.message.edit_text(
        f"{task_id}. ✅ {task[1]}",
        reply_markup=task_keyboard(task_id, True)
    )
@dp.callback_query(F.data.startswith("delete:"))
async def delete_callback(callback: CallbackQuery):
    if not isinstance(callback.message, Message):
        await callback.answer("Открой список задач заново.")
        return

    try:
        task_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Некорректный номер задачи.")
        return

    if not 1 <= task_id <= 9223372036854775807:
        await callback.answer("Некорректный номер задачи.")
        return

    deleted = delete_task(callback.from_user.id, task_id)

    if not deleted:
        await callback.answer("Задача уже удалена или не найдена.")
        return

    await callback.answer("Задача удалена 🗑")

    await callback.message.edit_text(
        f"🗑 Задача №{task_id} удалена.",
        reply_markup=None
    )
async def main():
    init_db()
    token = os.getenv("BOT_TOKEN", "").strip()

    if not token:
        raise RuntimeError("Добавь BOT_TOKEN в файл .env")

    bot = Bot(token=token)

    print("Бот запускается. Остановка — кнопка Stop.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())