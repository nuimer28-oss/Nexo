import os
import sys
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import minecraft_launcher_lib
import shutil
import uuid
import traceback

# --- Конфигурация ---
# Определяем путь к папке с приложением (работает и для .py, и для .exe)
if getattr(sys, 'frozen', False):
    # Если запущено из exe, берем папку, где лежит exe
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Если запущено из .py, берем папку со скриптом
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Остальные настройки...
APPDATA_DIR = os.path.join(os.getenv('APPDATA'), 'NexoLauncher')
os.makedirs(APPDATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APPDATA_DIR, "launcher_config.json")

DEFAULT_MIRROR = "https://bmclapi2.bangbang93.com"
MC_VERSION = "1.21.1"

# Цвета тёмной темы
BG_COLOR = "#2b2b2b"
FG_COLOR = "#e0e0e0"
ENTRY_BG = "#3c3f41"
ENTRY_FG = "#ffffff"
BTN_BG = "#4c5052"
BTN_FG = "#ffffff"
BTN_ACTIVE_BG = "#5c6062"
LOG_BG = "#1e1e1e"
LOG_FG = "#4caf50"

# Стандартные настройки
DEFAULT_CONFIG = {
    "nickname": "Player",
    "ram": "4",
    "game_dir": "app",
    "custom_game_dir": "",
    "mirror": DEFAULT_MIRROR,
    "delete_old": True,
    "java_path": ""
}

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Nexo")
        self.root.geometry("640x680")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        self.config = self.load_config()

        self.nickname_var = tk.StringVar(value=self.config["nickname"])
        self.ram_var = tk.StringVar(value=self.config["ram"])
        self.mirror_var = tk.StringVar(value=self.config["mirror"])
        self.game_dir_var = tk.StringVar(value=self.config["game_dir"])
        self.custom_dir_var = tk.StringVar(value=self.config["custom_game_dir"])
        self.delete_old_var = tk.BooleanVar(value=self.config["delete_old"])
        self.java_path_var = tk.StringVar(value=self.config["java_path"])

        self.create_widgets()
        self.log("Рекомендуется нажать 'Проверить / Обновить' перед первым запуском.", LOG_FG)

    def find_installed_java(self, game_dir, for_install=False):
        """Ищет Java, скачанную самим лаунчером в папке runtime.
        for_install=True — возвращает java.exe (с консолью, нужен для установщика NeoForge)
        for_install=False — возвращает javaw.exe (без консоли, для запуска игры)
        """
        runtime_dir = os.path.join(game_dir, "runtime")
        if not os.path.exists(runtime_dir):
            return None

        exe_name = "java.exe" if for_install else "javaw.exe"

        for runtime_name in os.listdir(runtime_dir):
            # Пропускаем файлы, ищем только папки
            runtime_path = os.path.join(runtime_dir, runtime_name)
            if not os.path.isdir(runtime_path):
                continue
            java_exe = os.path.join(runtime_path, "windows-x64", runtime_name, "bin", exe_name)
            if os.path.exists(java_exe):
                return java_exe
        return None

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key in DEFAULT_CONFIG:
                        if key not in config:
                            config[key] = DEFAULT_CONFIG[key]
                    return config
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        self.config["nickname"] = self.nickname_var.get()
        self.config["ram"] = self.ram_var.get()
        self.config["mirror"] = self.mirror_var.get()
        self.config["game_dir"] = self.game_dir_var.get()
        self.config["custom_game_dir"] = self.custom_dir_var.get()
        self.config["delete_old"] = self.delete_old_var.get()
        self.config["java_path"] = self.java_path_var.get()

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")
            return False

    def create_widgets(self):
        # --- Рамка настроек ---
        settings_frame = tk.LabelFrame(self.root, text="Настройки", padx=10, pady=10, 
                                       bg=BG_COLOR, fg=FG_COLOR, bd=1, relief="solid")
        settings_frame.pack(fill="x", padx=10, pady=5)

        # Никнейм
        tk.Label(settings_frame, text="Никнейм:", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(settings_frame, textvariable=self.nickname_var, width=20, 
                 bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR).grid(row=0, column=1, sticky="w", padx=5)

        # ОЗУ
        tk.Label(settings_frame, text="ОЗУ (ГБ):", bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=2, sticky="w", padx=(20, 0))
        tk.Entry(settings_frame, textvariable=self.ram_var, width=5, 
                 bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR).grid(row=0, column=3, sticky="w", padx=5)

        # Зеркало
        tk.Label(settings_frame, text="Зеркало/API:", bg=BG_COLOR, fg=FG_COLOR).grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(settings_frame, textvariable=self.mirror_var, width=45, 
                 bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR).grid(row=1, column=1, columnspan=3, sticky="we", padx=5)

        # Директория игры
        dir_frame = tk.Frame(settings_frame, bg=BG_COLOR)
        dir_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=5)

        tk.Radiobutton(dir_frame, text="В папке приложения", variable=self.game_dir_var, value="app",
                       command=self.toggle_dir_entry, bg=BG_COLOR, fg=FG_COLOR, selectcolor=BG_COLOR).pack(side="left")
        tk.Radiobutton(dir_frame, text="Указать путь:", variable=self.game_dir_var, value="custom",
                       command=self.toggle_dir_entry, bg=BG_COLOR, fg=FG_COLOR, selectcolor=BG_COLOR).pack(side="left", padx=(10, 0))
        
        self.dir_entry = tk.Entry(dir_frame, textvariable=self.custom_dir_var, width=25, 
                                  bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR)
        self.dir_entry.pack(side="left", padx=5)
        
        self.browse_btn = tk.Button(dir_frame, text="...", command=self.browse_directory, 
                                    bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG, activeforeground=FG_COLOR, width=3)
        self.browse_btn.pack(side="left")

        # Java Путь
        java_frame = tk.Frame(settings_frame, bg=BG_COLOR)
        java_frame.grid(row=3, column=0, columnspan=4, sticky="we", pady=5)

        tk.Label(java_frame, text="Java:", bg=BG_COLOR, fg=FG_COLOR).pack(side="left")
        tk.Entry(java_frame, textvariable=self.java_path_var, width=50, 
                 bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=FG_COLOR).pack(side="left", padx=5)
        
        java_browse_btn = tk.Button(java_frame, text="...", command=self.browse_java, 
                                    bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG, activeforeground=FG_COLOR, width=3)
        java_browse_btn.pack(side="left")

        # Чекбокс удаления старых версий
        tk.Checkbutton(settings_frame, text="Удалять старые версии NeoForge при обновлении", 
                       variable=self.delete_old_var, bg=BG_COLOR, fg=FG_COLOR, selectcolor=BG_COLOR).grid(row=4, column=0, columnspan=4, sticky="w", pady=(5, 0))

        self.toggle_dir_entry()

        # --- Кнопки управления (ПАКУЕМ ИХ ПЕРВЫМИ, ЧТОБЫ ОНИ НЕ ИСЧЕЗАЛИ) ---
        btn_frame = tk.Frame(self.root, bg=BG_COLOR)
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.update_btn = tk.Button(btn_frame, text="Проверить / Обновить", command=self.start_update_thread,
                                    bg=BTN_BG, fg=BTN_FG, activebackground=BTN_ACTIVE_BG, activeforeground=FG_COLOR, height=2)
        self.update_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.play_btn = tk.Button(btn_frame, text="ИГРАТЬ", command=self.start_game_thread, 
                                  bg="#4CAF50", fg="white", activebackground="#45a049", activeforeground="white", 
                                  font=("Arial", 10, "bold"), height=2)
        self.play_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # --- Рамка лога (ПАКУЕМ ПОСЛЕ КНОПОК, ЧТОБЫ ОНА ЗАНИМАЛА ОСТАВШЕЕСЯ МЕСТО) ---
        log_frame = tk.LabelFrame(self.root, text="Лог установки и запуска", padx=5, pady=5, 
                                   bg=BG_COLOR, fg=FG_COLOR, bd=1, relief="solid")
        log_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, bg=LOG_BG, fg=LOG_FG, font=("Consolas", 9), wrap="word", bd=0)
        self.log_text.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=BTN_BG, troughcolor=BG_COLOR)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def toggle_dir_entry(self):
        if self.game_dir_var.get() == "custom":
            self.dir_entry.config(state="normal", bg=ENTRY_BG)
            self.browse_btn.config(state="normal")
        else:
            self.dir_entry.config(state="disabled", bg=BG_COLOR)
            self.browse_btn.config(state="disabled")

    def browse_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.custom_dir_var.set(path)

    def browse_java(self):
        filetypes = [("Java Executable", "javaw.exe java.exe java"), ("All Files", "*.*")]
        path = filedialog.askopenfilename(title="Выберите исполняемый файл Java", filetypes=filetypes)
        if path:
            self.java_path_var.set(path)

    def get_game_directory(self):
        if self.game_dir_var.get() == "app":
            return os.path.join(APP_DIR, "minecraft")
        else:
            custom = self.custom_dir_var.get().strip()
            if not custom:
                return os.path.join(APP_DIR, "minecraft")
            return custom

    def log(self, message, color=LOG_FG):
        self.log_text.insert(tk.END, message + "\n", color)
        self.log_text.see(tk.END)
        self.root.update()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def set_status(self, text):
        self.root.title(f"Nexo - {text}")
        self.log(text, LOG_FG)

    def check_write_permissions(self, path):
        """Проверяет, есть ли права на запись в указанную папку."""
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".write_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False

    def get_latest_neoforge_version(self, game_dir):
        versions_dir = os.path.join(game_dir, "versions")
        if not os.path.exists(versions_dir):
            return None
        
        neoforge_versions = []
        for folder in os.listdir(versions_dir):
            if folder.lower().startswith("neoforge-"):
                if "21.1" in folder:
                    json_path = os.path.join(versions_dir, folder, f"{folder}.json")
                    if os.path.exists(json_path):
                        neoforge_versions.append(folder)
        
        if not neoforge_versions:
            return None
        
        def parse_version(v_str):
            parts = v_str.replace("neoforge-", "").split(".")
            try:
                return [int(p) for p in parts]
            except ValueError:
                return [0, 0, 0]
        
        neoforge_versions.sort(key=parse_version, reverse=True)
        return neoforge_versions[0]

    def cleanup_old_neoforge_versions(self, game_dir, keep_version):
        versions_dir = os.path.join(game_dir, "versions")
        if not os.path.exists(versions_dir):
            return
        
        for folder in os.listdir(versions_dir):
            if folder.lower().startswith("neoforge-") and folder != keep_version:
                if "21.1" in folder:
                    folder_path = os.path.join(versions_dir, folder)
                    try:
                        shutil.rmtree(folder_path)
                        self.log(f"Удалена старая версия: {folder}", "#ffaa00")
                    except Exception as e:
                        self.log(f"Не удалось удалить {folder}: {e}", "#ff5555")

    def start_update_thread(self):
        self.update_btn.config(state="disabled")
        self.play_btn.config(state="disabled")
        self.clear_log()
        thread = threading.Thread(target=self.install_game, daemon=True)
        thread.start()

    def start_game_thread(self):
        self.play_btn.config(state="disabled")
        thread = threading.Thread(target=self.launch_game, daemon=True)
        thread.start()

    def install_game(self):
        try:
            if not self.save_config():
                self.log("Ошибка: Не удалось сохранить настройки.", "#ff5555")
                return

            game_dir = self.get_game_directory()
            
            # Проверка прав на запись
            if not self.check_write_permissions(game_dir):
                self.log(f"Ошибка: Нет прав на запись в папку: {game_dir}", "#ff5555")
                messagebox.showerror("Ошибка доступа", 
                                     f"Нет прав на запись в папку:\n{game_dir}\n\n"
                                     "Пожалуйста, выберите другую папку (например, на рабочем столе или диске D:) "
                                     "или запустите лаунчер от имени администратора.")
                return

            self.set_status("Начало установки Minecraft...")

            # 1. Устанавливаем Minecraft (заодно скачается Java 21)
            self.set_status("Установка Minecraft 1.21.1...")
            minecraft_launcher_lib.install.install_minecraft_version(
                MC_VERSION, 
                game_dir,
                callback={
                    "setStatus": lambda text: self.set_status(text),
                    "setProgress": lambda value: None,
                    "setMax": lambda maximum: None
                }
            )

            # 2. Устанавливаем NeoForge
            self.set_status("Установка NeoForge...")
            
            # Ищем скачанную Java (java.exe — с консолью, нужен для установщика NeoForge)
            java_for_install = self.find_installed_java(game_dir, for_install=True)
            
            if java_for_install:
                self.log(f"Используется Java для установщика: {java_for_install}", LOG_FG)
            else:
                # Резервный вариант: берём указанную пользователем или системную
                java_for_install = self.java_path_var.get().strip() or "java"
                self.log(f"Скачанная Java не найдена, используется: {java_for_install}", "#ffaa00")
            
            neoforge_loader = minecraft_launcher_lib.mod_loader.get_mod_loader("neoforge")
            neoforge_loader.install(MC_VERSION, game_dir, java=java_for_install)
            
            self.set_status("Установка завершена успешно!")
            self.log("Minecraft и NeoForge установлены.", LOG_FG)

            if self.delete_old_var.get():
                latest = self.get_latest_neoforge_version(game_dir)
                if latest:
                    self.cleanup_old_neoforge_versions(game_dir, latest)
                    self.log(f"Оставлена актуальная версия: {latest}", LOG_FG)

        except Exception as e:
            self.log(f"Ошибка установки: {e}", "#ff5555")
            self.log(traceback.format_exc(), "#ff5555")
            messagebox.showerror("Ошибка", f"Ошибка установки: {e}")
        finally:
            self.update_btn.config(state="normal")
            self.play_btn.config(state="normal")

    def launch_game(self):
        try:
            if not self.save_config():
                self.log("Ошибка: Не удалось сохранить настройки.", "#ff5555")
                return

            game_dir = self.get_game_directory()
            nickname = self.nickname_var.get().strip()
            ram_gb = self.ram_var.get().strip()
            java_path = self.java_path_var.get().strip()

            if not nickname:
                messagebox.showerror("Ошибка", "Введите никнейм!")
                return

            if not self.check_write_permissions(game_dir):
                self.log(f"Ошибка: Нет прав на запись в папку: {game_dir}", "#ff5555")
                messagebox.showerror("Ошибка доступа", f"Нет прав на запись в папку:\n{game_dir}")
                return

            self.log(f"Запуск Minecraft с ником: {nickname}", LOG_FG)
            self.log(f"Выделено ОЗУ: {ram_gb} ГБ", LOG_FG)
            
            try:
                ram_int = int(ram_gb)
                if ram_int < 1: ram_int = 1
            except ValueError:
                ram_int = 4
            
            jvm_args = [
                f"-Xmx{ram_int}G",
                f"-Xms{max(1, ram_int // 2)}G"
            ]

            latest_neoforge = self.get_latest_neoforge_version(game_dir)
            if not latest_neoforge:
                self.log("Ошибка: Не найдена установленная версия NeoForge. Нажмите 'Проверить / Обновить'.", "#ff5555")
                messagebox.showerror("Ошибка", "NeoForge не установлен. Нажмите 'Проверить / Обновить'.")
                return

            self.log(f"Найдена версия для запуска: {latest_neoforge}", LOG_FG)
            
            # --- УМНЫЙ ПОИСК JAVA ---
            # 1. Сначала ищем скачанную лаунчером Java 21 (javaw.exe — без консоли)
            downloaded_java = self.find_installed_java(game_dir, for_install=False)
            
            if downloaded_java:
                executable = downloaded_java
                self.log("Используется встроенная Java 21 (без консоли).", LOG_FG)
            elif java_path and os.path.exists(java_path):
                executable = java_path
                self.log(f"Используется указанная Java: {java_path}", LOG_FG)
            else:
                executable = "java"
                self.log("Внимание: скачанная Java не найдена, используется системная Java.", "#ffaa00")

            # Диагностика (полезно для отладки)
            self.log(f"Итоговый путь к Java: {executable}", LOG_FG)
            self.log(f"Файл существует: {os.path.exists(executable) if os.path.sep in executable else 'проверить в PATH'}", LOG_FG)

            # Генерация оффлайн UUID
            player_uuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{nickname}"))

            options = {
                "username": nickname,
                "uuid": player_uuid,
                "token": "",
                "jvmArguments": jvm_args,
                "executablePath": executable,
                "gameDirectory": game_dir
            }

            command = minecraft_launcher_lib.command.get_minecraft_command(
                latest_neoforge,
                game_dir,
                options
            )

            self.log("Запуск игры...", LOG_FG)
            subprocess.Popen(command)
            self.log("Игра запущена.", LOG_FG)

        except Exception as e:
            self.log(f"Ошибка запуска: {e}", "#ff5555")
            self.log(traceback.format_exc(), "#ff5555")
            messagebox.showerror("Ошибка", f"Не удалось запустить игру: {e}")
        finally:
            self.play_btn.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftLauncher(root)
    root.mainloop()