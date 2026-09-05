import csv
import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
CSV_FILE_PATH = "orders.csv"
DASHBOARD_URL = "http://127.0.0.1:8050/"
BOT_TOKEN = "8995710469:AAHJm_AeGL-3FBpf2t2DSclxE1QvO7aJQVw"  # Оставлен тот же токен

# Глобальный словарь заказов
orders = {}

# ------------------- Работа с CSV -------------------
def load_from_csv():
    """Загружает заказы из CSV-файла в глобальный словарь orders."""
    global orders
    orders = {}
    if not os.path.exists(CSV_FILE_PATH):
        return
    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # пропускаем заголовок
            for row in reader:
                if len(row) >= 7:
                    try:
                        order_id = int(row[0])
                        orders[order_id] = {
                            'client': row[1],
                            'service': row[2],
                            'deadline': row[3],
                            'budget': float(row[4]),
                            'status': row[5],
                            'manager': row[6]
                        }
                    except (ValueError, IndexError):
                        logger.warning(f"Пропущена некорректная строка: {row}")
    except Exception as e:
        logger.error(f"Ошибка при загрузке CSV: {e}")

def save_to_csv():
    """Сохраняет текущие заказы в CSV-файл."""
    rows = [['OrderID', 'Client', 'Service', 'Deadline', 'Budget', 'Status', 'Manager']]
    for order_id, info in orders.items():
        rows.append([
            str(order_id),
            info['client'],
            info['service'],
            info['deadline'],
            str(info['budget']),
            info['status'],
            info['manager']
        ])
    try:
        with open(CSV_FILE_PATH, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except Exception as e:
        logger.error(f"Ошибка при сохранении CSV: {e}")

# ------------------- Обработчики команд -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start – приветственное сообщение."""
    await update.message.reply_text(
        "Привет! Я бот управления заказами консалтинговой компании. "
        "Используй команды:\n"
        "/add - добавить новый заказ\n"
        "/update - обновить заказ\n"
        "/delete - удалить заказ\n"
        "/list - список заказов\n"
        "/info - детальная информация\n"
        "/status - изменить статус\n"
        "/manager - назначить менеджера\n"
        "/dashboard - аналитический дашборд"
    )

async def add_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add – добавить новый заказ."""
    try:
        # Получаем текст после команды
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Нет аргументов")
        parts = [p.strip() for p in args[1].split(',')]
        if len(parts) != 4:
            raise ValueError("Неверное количество полей")
        client, service, deadline, budget_str = parts
        budget = float(budget_str)
    except Exception:
        await update.message.reply_text(
            "Ошибка в формате ввода. Используйте:\n"
            "/add Клиент, Услуга, Срок_исполнения, Бюджет\n"
            "Пример: /add ООО Рога и копыта, Бизнес-консалтинг, 2024-10-10, 50000"
        )
        return

    # Генерируем ID
    order_id = max(orders.keys(), default=0) + 1
    orders[order_id] = {
        'client': client,
        'service': service,
        'deadline': deadline,
        'budget': budget,
        'status': 'Новый',
        'manager': 'Не назначен'
    }
    save_to_csv()
    await update.message.reply_text(f"Заказ №{order_id} успешно создан!")

async def update_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /update – обновить поле заказа."""
    try:
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Нет аргументов")
        parts = [p.strip() for p in args[1].split(',')]
        if len(parts) < 3:
            raise ValueError("Неверное количество полей")
        order_id_str = parts[0]
        field = parts[1]
        value = ','.join(parts[2:]).strip()
        if not order_id_str or not field or not value:
            raise ValueError("Пустые значения")
        order_id = int(order_id_str)
    except Exception:
        await update.message.reply_text(
            "Ошибка в формате ввода. Используйте:\n"
            "/update номер_заказа, поле, значение\n"
            "Пример: /update 12345, срок_исполнения, 2024-09-10"
        )
        return

    if order_id not in orders:
        await update.message.reply_text(f"Заказ №{order_id} не найден")
        return

    if field not in orders[order_id]:
        await update.message.reply_text("Указанное поле не существует")
        return

    # Преобразование типа для числовых полей при необходимости
    if field == 'budget':
        try:
            orders[order_id][field] = float(value)
        except ValueError:
            await update.message.reply_text("Бюджет должен быть числом")
            return
    else:
        orders[order_id][field] = value

    save_to_csv()
    await update.message.reply_text(f"Заказ №{order_id} успешно обновлен!")

async def delete_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete – удалить заказ."""
    try:
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Нет ID")
        order_id = int(args[1].strip())
    except Exception:
        await update.message.reply_text("Используйте: /delete номер_заказа")
        return

    if order_id not in orders:
        await update.message.reply_text(f"Заказ №{order_id} не найден")
        return

    del orders[order_id]
    save_to_csv()
    await update.message.reply_text(f"Заказ №{order_id} удален!")

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list – список всех заказов."""
    if not orders:
        await update.message.reply_text("Заказов нет")
        return

    lines = []
    for oid, info in orders.items():
        lines.append(f"№{oid}: {info['client']} - {info['service']} ({info['status']})")
    await update.message.reply_text("Список заказов:\n" + "\n".join(lines))

async def order_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /info – детальная информация о заказе."""
    try:
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Нет ID")
        order_id = int(args[1].strip())
    except Exception:
        await update.message.reply_text("Используйте: /info номер_заказа")
        return

    if order_id not in orders:
        await update.message.reply_text(f"Заказ №{order_id} не найден")
        return

    info = orders[order_id]
    text = (
        f"Детальная информация о заказе №{order_id}:\n"
        f"Клиент: {info['client']}\n"
        f"Услуга: {info['service']}\n"
        f"Срок исполнения: {info['deadline']}\n"
        f"Бюджет: {info['budget']}\n"
        f"Статус: {info['status']}\n"
        f"Менеджер: {info['manager']}"
    )
    await update.message.reply_text(text)

async def change_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /status – изменить статус заказа."""
    try:
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Нет аргументов")
        parts = [p.strip() for p in args[1].split(',')]
        if len(parts) != 2:
            raise ValueError("Неверное количество полей")
        order_id = int(parts[0])
        new_status = parts[1]
        if not new_status:
            raise ValueError("Пустой статус")
    except Exception:
        await update.message.reply_text(
            "Используйте: /status номер_заказа, новый_статус\n"
            "Пример: /status 12345, В работе"
        )
        return

    if order_id not in orders:
        await update.message.reply_text(f"Заказ №{order_id} не найден")
        return

    orders[order_id]['status'] = new_status
    save_to_csv()
    await update.message.reply_text(f"Статус заказа №{order_id} изменен на \"{new_status}\"")

async def assign_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /manager – назначить менеджера на заказ."""
    try:
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            raise ValueError("Нет аргументов")
        parts = [p.strip() for p in args[1].split(',')]
        if len(parts) != 2:
            raise ValueError("Неверное количество полей")
        order_id = int(parts[0])
        manager = parts[1]
        if not manager:
            raise ValueError("Пустое имя менеджера")
    except Exception:
        await update.message.reply_text(
            "Используйте: /manager номер_заказа, ФИО_менеджера\n"
            "Пример: /manager 12345, Иванов И.И."
        )
        return

    if order_id not in orders:
        await update.message.reply_text(f"Заказ №{order_id} не найден")
        return

    orders[order_id]['manager'] = manager
    save_to_csv()
    await update.message.reply_text(f"На заказ №{order_id} назначен менеджер: {manager}")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /dashboard – ссылка на дашборд."""
    await update.message.reply_text(f"Аналитический дашборд: {DASHBOARD_URL}")

# ------------------- Основная функция -------------------
def main():
    """Запуск бота."""
    # Загружаем данные из CSV
    load_from_csv()
    logger.info("Данные загружены. Количество заказов: %d", len(orders))

    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_order))
    application.add_handler(CommandHandler("update", update_order))
    application.add_handler(CommandHandler("delete", delete_order))
    application.add_handler(CommandHandler("list", list_orders))
    application.add_handler(CommandHandler("info", order_info))
    application.add_handler(CommandHandler("status", change_status))
    application.add_handler(CommandHandler("manager", assign_manager))
    application.add_handler(CommandHandler("dashboard", dashboard))

    # Запускаем бота
    logger.info("Бот управления заказами запущен. Ожидание обновлений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()