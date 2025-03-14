import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    """Создает таблицу, если её нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                commands_used INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def add_user(user_id: int):
    """Добавляет пользователя, если его нет в БД"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id) VALUES (?)
        """, (user_id,))
        await db.commit()

async def increment_command_count(user_id: int):
    """Увеличивает количество использованных команд"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET commands_used = commands_used + 1 WHERE user_id = ?
        """, (user_id,))
        await db.commit()

async def get_user_stats(user_id: int):
    """Возвращает количество команд, использованных пользователем"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT commands_used FROM users WHERE user_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_all_users():
    """Возвращает список всех user_id из базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
