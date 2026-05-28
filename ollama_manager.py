import tkinter as tk
import subprocess
import threading
import os
import sys
import signal
import time
import webbrowser

class OllamaManager:
    def __init__(self, root):
        self.root = root
        root.title("Ollama Service") # Исправил написание на Service
        root.geometry("800x600")
        root.configure(bg="#212121")
        
        # --- ДИНАМИЧЕСКИЙ ПУТЬ ---
        # Определяет папку запуска: либо рядом со скриптом, либо внутри .app
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(os.path.abspath(sys.executable))
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.log_file = os.path.join(self.base_path, 'ollama_daemon.log')
        self.icon_path = os.path.join(self.base_path, 'icon.icns')

        self.log_offset = 0
        self.process = None
        self.is_running = False

        # --- ИНТЕРФЕЙС ---
        self.top_frame = tk.Frame(root, bg="#2d2d2d", height=70)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        self.top_frame.pack_propagate(False)

        self.lbl_status = tk.Label(self.top_frame, text="  СТАТУС: ОСТАНОВЛЕН", bg="#2d2d2d", fg="#ff4444", font=("Helvetica", 14, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=20, pady=15)

        # Кнопка СТАРТ
        self.lbl_start = tk.Label(self.top_frame, text="▶ ЗАПУСТИТЬ", bg="#28a745", fg="white", font=("Helvetica", 12, "bold"), padx=20, pady=10, cursor="hand2")
        self.lbl_start.pack(side=tk.RIGHT, padx=10, pady=10)
        self.lbl_start.bind("<Button-1>", lambda e: self.start_ollama())

        # Кнопка СТОП
        self.lbl_stop = tk.Label(self.top_frame, text="⏹ ОСТАНОВИТЬ", bg="#555555", fg="#888888", font=("Helvetica", 12, "bold"), padx=20, pady=10)
        self.lbl_stop.pack(side=tk.RIGHT, padx=10, pady=10)

        # Кнопка ОТКРЫТЬ ЛОГ
        self.lbl_open_log = tk.Label(self.top_frame, text="📂 ЛОГ", bg="#007aff", fg="white", font=("Helvetica", 12, "bold"), padx=20, pady=10, cursor="hand2")
        self.lbl_open_log.pack(side=tk.RIGHT, padx=10, pady=10)
        self.lbl_open_log.bind("<Button-1>", lambda e: self.open_log())

        # Окно логов
        self.log_frame = tk.Frame(root, bg="#1a1a1a")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Текстовое поле (state=DISABLED позволяет выделение, но запрещает ввод)
        self.txt_log = tk.Text(self.log_frame, bg="#000000", fg="#00ff00", font=("Menlo", 11), state=tk.DISABLED, 
                               borderwidth=0, highlightthickness=0, selectbackground="#004400", selectforeground="#ffffff")
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scroll = tk.Scrollbar(self.log_frame, command=self.txt_log.yview)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.config(yscrollcommand=self.scroll.set)

        # --- ПРИВЯЗКИ КОПИРОВАНИЯ ---
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=self.copy_log_selection)
        self.txt_log.bind("<Button-2>", self.show_context_menu)
        self.txt_log.bind("<Button-3>", self.show_context_menu)
        self.txt_log.bind("<Command-c>", lambda e: self.txt_log.event_generate("<<Copy>>"))

        # Ховер-эффекты
        self.lbl_start.bind("<Enter>", lambda e: self.lbl_start.config(bg="#218838"))
        self.lbl_start.bind("<Leave>", lambda e: self.lbl_start.config(bg="#28a745"))
        self.lbl_open_log.bind("<Enter>", lambda e: self.lbl_open_log.config(bg="#0056b3"))
        self.lbl_open_log.bind("<Leave>", lambda e: self.lbl_open_log.config(bg="#007aff"))

        # Попытка установить иконку
        self.load_icon()

        # Запуск мониторинга
        self.monitor_thread = threading.Thread(target=self._tail_log, daemon=True)
        self.monitor_thread.start()

                # --- НАСТРОЙКА МЕНЮ ---
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Создаем меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        # Бинд стандартной клавиши Mac "Cmd + ," для вызова "О программе"
        self.root.bind('<Command-,>', lambda e: self.show_about())

    def load_icon(self):
        if os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except tk.TclError:
                try:
                    img = tk.PhotoImage(file=self.icon_path)
                    self.root.tk.call('wm', 'iconphoto', self.root._w, img)
                except:
                    pass

    def _find_ollama_executable(self):
        # 1. Проверяем стандартную установку через .app
        app_path = "/Applications/Ollama.app/Contents/Resources/ollama"
        if os.path.exists(app_path):
            return app_path
        
        # 2. Проверяем Homebrew (Intel Mac)
        brew_path = "/usr/local/bin/ollama"
        if os.path.exists(brew_path):
            return brew_path

        # 3. Проверяем Homebrew (Apple Silicon Mac)
        brew_arm_path = "/opt/homebrew/bin/ollama"
        if os.path.exists(brew_arm_path):
            return brew_arm_path

        # 4. Фоллбек на системный поиск
        return "ollama"

    def open_log(self):
        if os.path.exists(self.log_file):
            subprocess.Popen(['open', self.log_file])
    
    def open_link(self, url):
        webbrowser.open(url)

    def show_about(self):
        # Создаем всплывающее окно
        about_win = tk.Toplevel(self.root)
        about_win.title("О программе")
        about_win.geometry("450x335")
        about_win.transient(self.root) # Поверх главного окна
        about_win.grab_set()           # Блокировка главного окна
        about_win.configure(bg="#2d2d2d")
        about_win.resizable(False, False)

        # Контент
        tk.Label(about_win, text="Ollama Service Manager", bg="#2d2d2d", fg="#ffffff", font=("Helvetica", 14, "bold")).pack(pady=(20, 5))
        tk.Label(about_win, text="Версия: 1.0", bg="#2d2d2d", fg="#aaaaaa").pack()
        
        # Разделитель
        tk.Frame(about_win, height=2, bg="#555555").pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(about_win, text="Утилита для запуска и мониторинга Ollama.", bg="#2d2d2d", fg="#cccccc").pack()
        
        tk.Label(about_win, text="⚠ ТРЕБОВАНИЯ:", bg="#2d2d2d", fg="#ffaa00", font=("Helvetica", 10, "bold")).pack(pady=(10,0))
        
                # Текст требования
        tk.Label(about_win, text="Для работы требуется установленная Ollama(0.24.0)\nв папке Програмы.", 
                 bg="#2d2d2d", fg="#cccccc").pack(pady=5)
        
        tk.Label(about_win, text="!!! ВАЖНО Ollama не запускать только установка.", 
                 bg="#2d2d2d", fg="#ff0000").pack(pady=5)

        # Ссылка 1: Сайт
        lbl_site = tk.Label(about_win, text="🌐 Сайт Ollama", fg="#007aff", bg="#2d2d2d", 
                            cursor="hand2", font=("Helvetica", 10, "underline"))
        lbl_site.pack(pady=2)
        lbl_site.bind("<Button-1>", lambda e: self.open_link("https://ollama.com"))
        lbl_site.bind("<Enter>", lambda e: lbl_site.config(fg="#0056b3"))
        lbl_site.bind("<Leave>", lambda e: lbl_site.config(fg="#007aff"))

        # Ссылка 2: Гитхаб
        tk.Label(about_win, text="\n Автор: Савченко Илья", bg="#2d2d2d", fg="#cccccc").pack()

        lbl_repo = tk.Label(about_win, text="💻 Репозиторий SavaLab", fg="#007aff", bg="#2d2d2d", 
                            cursor="hand2", font=("Helvetica", 10, "underline"))
        lbl_repo.pack(pady=2)
        lbl_repo.bind("<Button-1>", lambda e: self.open_link("https://github.com/sava-74/ollama_servise")) # Убрал .git для корректного открытия в браузере
        lbl_repo.bind("<Enter>", lambda e: lbl_repo.config(fg="#0056b3"))
        lbl_repo.bind("<Leave>", lambda e: lbl_repo.config(fg="#007aff"))

        
        # tk.Button(about_win, text="OK", command=about_win.destroy, bg="#262626", fg="#39B221", relief=tk.FLAT, width=10).pack(pady=15)


    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def copy_log_selection(self):
        self.txt_log.event_generate('<<Copy>>')

    def start_ollama(self):
        if self.is_running: return
        self.is_running = True
        self._set_status("ЗАПУСК...", "#ffaa00")
        self._disable_start()

        def run():
            try:
                open(self.log_file, 'w').close()
                self.log_offset = 0

                # --- ИСПРАВЛЕНИЕ ПУТИ ---
                ollama_bin = self._find_ollama_executable()
                if ollama_bin == "ollama":
                    # Если не нашли конкретный файл, пробуем расширить PATH для поиска
                    env = os.environ.copy()
                    env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:" + env.get("PATH", "")
                else:
                    env = os.environ.copy()
                
                env["OLLAMA_HOST"] = "0.0.0.0:11434"
                env["OLLAMA_KEEP_ALIVE"] = "-1"
                env["OLLAMA_NO_CLOUD"] = "true"

                # Запуск с найденным путем
                with open(self.log_file, "a") as f:
                    self.process = subprocess.Popen([ollama_bin, "serve"], env=env, stdout=f, stderr=subprocess.STDOUT)

                self.root.after(0, self._on_started)
                self.process.wait()
                self.root.after(0, self._on_stopped)

            except PermissionError:
                self.root.after(0, lambda: self._log("ОШИБКА: Нет прав на запись лога.\n"))
                self.root.after(0, self._on_stopped)
            except Exception as e:
                self.root.after(0, lambda: self._log(f"ОШИБКА: {str(e)}\n"))
                self.root.after(0, self._on_stopped)

        threading.Thread(target=run, daemon=True).start()

    def stop_ollama(self):
        if not self.is_running: return
        self._set_status("ОСТАНОВКА...", "#ffaa00")
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except:
                    pass
        self._on_stopped()

    def _on_started(self):
        self._set_status("РАБОТАЕТ", "#00ff00")
        self._enable_stop()

    def _on_stopped(self):
        self.is_running = False
        self.process = None
        self._set_status("ОСТАНОВЛЕН", "#ff4444")
        self._enable_start()
        self._disable_stop()

    def _set_status(self, text, color):
        self.lbl_status.config(text=f"  СТАТУС: {text}", fg=color)

    def _enable_stop(self):
        self.lbl_stop.config(bg="#dc3545", fg="white", cursor="hand2")
        self.lbl_stop.bind("<Button-1>", lambda e: self.stop_ollama())
        self.lbl_stop.bind("<Enter>", lambda e: self.lbl_stop.config(bg="#c82333"))
        self.lbl_stop.bind("<Leave>", lambda e: self.lbl_stop.config(bg="#dc3545"))

    def _disable_stop(self):
        self.lbl_stop.config(bg="#555555", fg="#888888", cursor="")
        self.lbl_stop.unbind("<Button-1>")
        self.lbl_stop.unbind("<Enter>")
        self.lbl_stop.unbind("<Leave>")

    def _disable_start(self):
        self.lbl_start.config(bg="#555555", fg="#888888", cursor="")
        self.lbl_start.unbind("<Button-1>")
        self.lbl_start.unbind("<Enter>")
        self.lbl_start.unbind("<Leave>")

    def _enable_start(self):
        self.lbl_start.config(bg="#28a745", fg="white", cursor="hand2")
        self.lbl_start.bind("<Button-1>", lambda e: self.start_ollama())
        self.lbl_start.bind("<Enter>", lambda e: self.lbl_start.config(bg="#218838"))
        self.lbl_start.bind("<Leave>", lambda e: self.lbl_start.config(bg="#28a745"))

    def _log(self, text):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, text)
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def _tail_log(self):
        while True:
            if os.path.exists(self.log_file):
                try:
                    with open(self.log_file, "r") as f:
                        f.seek(self.log_offset)
                        new_data = f.read()
                        self.log_offset = f.tell()
                        if new_data:
                            self.root.after(0, self._log, new_data)
                except: pass
            time.sleep(0.2)

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaManager(root)
    root.mainloop()