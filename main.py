import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import os

# Для Jinja2
from jinja2 import Environment, FileSystemLoader

HOST = "127.0.0.1"
PORT = 8080

# Инициализация окружения для Jinja2
# Важно, что шаблоны лежат в папке "templates" на том же уровне
env = Environment(loader=FileSystemLoader("templates"))


def init_db():
    """
    Создаёт таблицу workers, если она ещё не создана.
    """
    with sqlite3.connect("workers.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT,
                department TEXT
            )
            """
        )
        conn.commit()


def get_all_workers():
    """
    Возвращает список всех работников из таблицы workers.
    """
    with sqlite3.connect("workers.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, position, department FROM workers")
        rows = cursor.fetchall()
        # Преобразуем в удобный формат (список словарей)
        workers = [
            {"id": row[0], "name": row[1], "position": row[2], "department": row[3]}
            for row in rows
        ]
    return workers


def get_worker_by_id(worker_id):
    """
    Возвращает данные конкретного работника по его id.
    """
    with sqlite3.connect("workers.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, position, department FROM workers WHERE id = ?",
            (worker_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {"id": row[0], "name": row[1], "position": row[2], "department": row[3]}


def add_worker(name, position, department):
    """
    Добавляет нового работника в таблицу workers.
    """
    with sqlite3.connect("workers.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workers (name, position, department) VALUES (?, ?, ?)",
            (name, position, department)
        )
        conn.commit()


def update_worker(worker_id, name, position, department):
    """
    Обновляет данные работника в таблице workers.
    """
    with sqlite3.connect("workers.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE workers SET name=?, position=?, department=? WHERE id=?",
            (name, position, department, worker_id)
        )
        conn.commit()


def delete_worker(worker_id):
    """
    Удаляет работника из таблицы workers.
    """
    with sqlite3.connect("workers.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workers WHERE id=?", (worker_id,))
        conn.commit()


class MyRequestHandler(BaseHTTPRequestHandler):
    """
    Обработчик HTTP-запросов.
    """

    def do_GET(self):
        """
        Обработка GET-запроса:
          - /                   => главная страница
          - /workers            => список работников
          - /workers/add        => форма для добавления работника
          - /workers/edit/<id>  => форма для редактирования работника
          - /workers/delete/<id> => удаление работника
        """
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip("/").split("/")

        if parsed_path.path == "/":
            # Главная страница
            template = env.get_template("index.html")
            content = template.render(title="Добро пожаловать в Кантерлот!")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        elif parsed_path.path == "/workers":
            # Вывод списка работников
            workers = get_all_workers()
            template = env.get_template("workers_list.html")
            content = template.render(workers=workers, title="Список работников")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        elif len(path_parts) == 2 and path_parts[0] == "workers" and path_parts[1] == "add":
            # Форма добавления работника
            template = env.get_template("worker_form.html")
            content = template.render(
                title="Добавление работника",
                action="/workers/add",
                worker=None,
                submit_text="Добавить"
            )
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        elif len(path_parts) == 3 and path_parts[0] == "workers" and path_parts[1] == "edit":
            # Форма редактирования работника
            worker_id = path_parts[2]
            worker = get_worker_by_id(worker_id)
            if worker:
                template = env.get_template("worker_form.html")
                content = template.render(
                    title=f"Редактирование работника #{worker_id}",
                    action=f"/workers/edit/{worker_id}",
                    worker=worker,
                    submit_text="Сохранить"
                )
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                self.send_error(404, "Worker not found")

        elif len(path_parts) == 3 and path_parts[0] == "workers" and path_parts[1] == "delete":
            # Удаление работника
            worker_id = path_parts[2]
            worker = get_worker_by_id(worker_id)
            if worker:
                delete_worker(worker_id)
                # Покажем простую страницу с сообщением или переадресуем обратно на список
                template = env.get_template("message.html")
                content = template.render(
                    title="Работник удалён",
                    message=f"Работник c ID={worker_id} удалён."
                )
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                self.send_error(404, "Worker not found")

        else:
            self.send_error(404, "Страница не найдена")

    def do_POST(self):
        """
        Обработка POST-запроса:
          - /workers/add         => добавить нового работника
          - /workers/edit/<id>   => обновить работника
        """
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip("/").split("/")

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        data_dict = dict(urllib.parse.parse_qsl(post_data))

        if parsed_path.path == "/workers/add":
            # Добавляем нового работника
            name = data_dict.get("name", "")
            position = data_dict.get("position", "")
            department = data_dict.get("department", "")
            add_worker(name, position, department)

            template = env.get_template("message.html")
            content = template.render(
                title="Успех",
                message=f"Новый работник '{name}' успешно добавлен!"
            )
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        elif len(path_parts) == 3 and path_parts[0] == "workers" and path_parts[1] == "edit":
            # Обновляем работника
            worker_id = path_parts[2]
            worker = get_worker_by_id(worker_id)
            if worker:
                name = data_dict.get("name", "")
                position = data_dict.get("position", "")
                department = data_dict.get("department", "")
                update_worker(worker_id, name, position, department)

                template = env.get_template("message.html")
                content = template.render(
                    title="Успех",
                    message=f"Данные работника с ID={worker_id} обновлены."
                )
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                self.send_error(404, "Worker not found")

        else:
            self.send_error(404, "Страница не найдена")


def run_server():
    """
    Запускает HTTP-сервер по заданным HOST и PORT.
    """
    init_db()
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, MyRequestHandler)
    print(f"Сервер запущен: http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
    httpd.server_close()


if __name__ == "__main__":
    run_server()
