import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os
import json  # Добавлен для парсинга прогресса
import re


class ModelManagerWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Управление моделями")
        self.geometry("700x550")
        self.configure(bg="#212121")
        
        self.transient(parent)
        self.resizable(True, True)
        
        self.ollama_bin = self._find_ollama()
        self.is_busy = False

        # --- ВЕРХНЯЯ ПАНЕЛЬ (Ввод) ---
        top_frame = tk.Frame(self, bg="#2d2d2d", height=60)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        top_frame.pack_propagate(False)

        tk.Label(top_frame, text="Имя модели:", bg="#2d2d2d", fg="white", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=5, pady=10)
        
        self.entry_name = tk.Entry(top_frame, bg="#1a1a1a", fg="#00ff00", insertbackground="#00ff00", font=("Menlo", 11), relief=tk.FLAT)
        self.entry_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=10)
        self.entry_name.focus_set()
        
        self.btn_pull = tk.Label(top_frame, text="⬇ СКАЧАТЬ", bg="#28a745", fg="white", font=("Helvetica", 10, "bold"), padx=15, pady=5, cursor="hand2")
        self.btn_pull.pack(side=tk.LEFT, padx=5, pady=10)
        self.btn_pull.bind("<Button-1>", lambda e: self.download_model())
        self.btn_pull.bind("<Enter>", lambda e: self.btn_pull.config(bg="#218838"))
        self.btn_pull.bind("<Leave>", lambda e: self.btn_pull.config(bg="#28a745"))

        self._setup_context_menu(self.entry_name, allow_paste=True)

        # --- СПИСОК МОДЕЛЕЙ ---
        list_frame = tk.Frame(self, bg="#1a1a1a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(list_frame, columns=("Name", "Size", "Modified"), show="headings", style="Custom.Treeview")
        self.tree.heading("Name", text="Название")
        self.tree.heading("Size", text="Размер")
        self.tree.heading("Modified", text="Обновлено")
        
        self.tree.column("Name", width=300, minwidth=150)
        self.tree.column("Size", width=80, anchor=tk.CENTER)
        self.tree.column("Modified", width=120)

        style = ttk.Style()
        style.configure("Custom.Treeview", background="#000000", foreground="#00ff00", fieldbackground="#000000", borderwidth=0, font=("Helvetica", 10))
        style.configure("Custom.Treeview.Heading", background="#333333", foreground="white", relief=tk.FLAT, font=("Helvetica", 10, "bold"))
        style.configure("Custom.Vertical.TScrollbar", background="#333333", troughcolor="#1a1a1a")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview, style="Custom.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_list()

        # --- ЛОГ ОПЕРАЦИЙ ---
        bottom_frame = tk.Frame(self, bg="#1a1a1a")
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(bottom_frame, text="Лог операций:", bg="#1a1a1a", fg="#888888", font=("Helvetica", 9), anchor="w").pack(fill=tk.X)

        self.txt_log = tk.Text(bottom_frame, bg="#000000", fg="#aaaaaa", font=("Menlo", 10), height=5, state=tk.DISABLED)
        self.txt_log.pack(fill=tk.X, pady=(0, 5))
        self._setup_context_menu(self.txt_log, allow_paste=False)

        # --- КНОПКИ УПРАВЛЕНИЯ ---
        btns_container = tk.Frame(self, bg="#2d2d2d", height=50)
        btns_container.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        btns_container.pack_propagate(False)

        self.btn_rm = tk.Label(btns_container, text="🗑 УДАЛИТЬ", bg="#dc3545", fg="white", font=("Helvetica", 10, "bold"), padx=15, pady=10, cursor="hand2")
        self.btn_rm.pack(side=tk.LEFT, padx=5, pady=5)
        self.btn_rm.bind("<Button-1>", lambda e: self.delete_model())
        self.btn_rm.bind("<Enter>", lambda e: self.btn_rm.config(bg="#c82333"))
        self.btn_rm.bind("<Leave>", lambda e: self.btn_rm.config(bg="#dc3545"))

        self.btn_refresh = tk.Label(btns_container, text="🔄 ОБНОВИТЬ", bg="#6c757d", fg="white", font=("Helvetica", 10, "bold"), padx=15, pady=10, cursor="hand2")
        self.btn_refresh.pack(side=tk.RIGHT, padx=5, pady=5)
        self.btn_refresh.bind("<Button-1>", lambda e: self.refresh_list())
        self.btn_refresh.bind("<Enter>", lambda e: self.btn_refresh.config(bg="#5a6268"))
        self.btn_refresh.bind("<Leave>", lambda e: self.btn_refresh.config(bg="#6c757d"))

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---

    def _setup_context_menu(self, widget, allow_paste=False):
        widget.bind("<Command-c>", lambda e: widget.event_generate("<<Copy>>"))
        widget.bind("<Command-v>", lambda e: widget.event_generate("<<Paste>>"))
        widget.bind("<Command-a>", lambda e: widget.event_generate("<<SelectAll>>"))
        widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
        widget.bind("<Control-a>", lambda e: widget.event_generate("<<SelectAll>>"))
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
        if allow_paste:
            menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="Выделить всё", command=lambda: widget.event_generate("<<SelectAll>>"))
        
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu)
        widget.bind("<Button-2>", show_menu)

    def _find_ollama(self):
        paths = [
            "/Applications/Ollama.app/Contents/Resources/ollama",
            "/usr/local/bin/ollama",
            "/opt/homebrew/bin/ollama"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return "ollama"

    def _log(self, text):
        # Вырезаем ANSI-коды (спиннеры, цвета) перед выводом
        clean_text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
        
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, clean_text + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    # --- ОСНОВНАЯ ЛОГИКА ---

    def refresh_list(self):
        if self.is_busy: return
        
        def run():
            try:
                self.is_busy = True
                self.after(0, self._log, "Проверка сервера...")
                
                env = os.environ.copy()
                env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
                env["OLLAMA_HOST"] = "http://localhost:11434" # Явно указываем адрес для CLI
                
                import time, urllib.request
                # Ждем открытия порта (макс 4 сек)
                server_ready = False
                for _ in range(4):
                    try:
                        urllib.request.urlopen("http://localhost:11434", timeout=1)
                        server_ready = True
                        break
                    except:
                        time.sleep(1)
                        
                if not server_ready:
                    self.after(0, lambda: self._log("Сервер не ответил. Нажмите 'Запустить' в главном окне."))
                    return

                self.after(0, self._log, "Обновление списка...")
                result = subprocess.run([self.ollama_bin, "list"], capture_output=True, text=True, env=env)
                
                if result.returncode != 0:
                    self.after(0, lambda: self._log(f"Ошибка: {result.stderr.strip()}"))
                    return

                lines = result.stdout.strip().split('\n')
                self.after(0, lambda: [self.tree.delete(i) for i in self.tree.get_children()])

                if len(lines) > 1:
                    for line in lines[1:]:
                        if not line.strip(): continue
                        parts = line.split()
                        if len(parts) >= 4:
                            name = parts[0]
                            units = ['B', 'KB', 'MB', 'GB', 'TB']
                            if parts[3] in units:
                                size_str = f"{parts[2]} {parts[3]}"
                                mod_idx = 4
                            else:
                                size_str = parts[2]
                                mod_idx = 3
                            modified = " ".join(parts[mod_idx:])
                            self.after(0, lambda n=name, s=size_str, m=modified: self.tree.insert("", "end", values=(n, s, m)))
                            
                self.after(0, lambda: self._log("Список обновлен."))
            except Exception as e:
                self.after(0, lambda: self._log(f"Ошибка: {str(e)}"))
            finally:
                self.after(0, lambda: setattr(self, 'is_busy', False))

        threading.Thread(target=run, daemon=True).start()

    def delete_model(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите модель для удаления")
            return

        model_name = self.tree.item(selection[0])['values'][0]
        
        if messagebox.askyesno("Подтверждение", f"Удалить модель {model_name}?"):
            def run():
                try:
                    self.is_busy = True
                    self.after(0, lambda: self._log(f"Удаление {model_name}..."))
                    
                    env = os.environ.copy()
                    env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")

                    subprocess.run([self.ollama_bin, "rm", model_name], check=True, env=env)

                    self.after(0, lambda: self._log(f"Модель {model_name} удалена."))
                    # self.after(0, self.refresh_list)
                except subprocess.CalledProcessError as e:
                    err = e.stderr.strip() if e.stderr else "Ошибка"
                    self.after(0, lambda: self._log(f"Ошибка удаления: {err}"))
                except Exception as e:
                    self.after(0, lambda: self._log(f"Ошибка: {str(e)}"))
                #finally:
                #    self.after(0, lambda: setattr(self, 'is_busy', False))
                finally:
                # 1. Снимаем блокировку
                    self.after(0, lambda: setattr(self, 'is_busy', False))
                # 2. И только теперь обновляем список
                    self.after(0, self.refresh_list)

            threading.Thread(target=run, daemon=True).start()

    def download_model(self):
        model_name = self.entry_name.get().strip()
        if not model_name:
            messagebox.showwarning("Внимание", "Введите имя модели")
            return

        # СРАЗУ очищаем поле, чтобы не было дублей при повторном клике
        self.entry_name.delete(0, tk.END)

        def run():
            try:
                self.is_busy = True
                self.btn_pull.config(state=tk.DISABLED)
                self.after(0, lambda: self._log(f"Загрузка {model_name}..."))
                
                env = os.environ.copy()
                env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + env.get("PATH", "")
                env["OLLAMA_HOST"] = "http://localhost:11434"

                process = subprocess.Popen([self.ollama_bin, "pull", model_name], 
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                           text=True, env=env)
                
                for line in process.stdout:
                    # Чистим строку от мусора перед обработкой
                    clean_line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line).strip()
                    
                    if clean_line:
                        self.after(0, self._log, clean_line)
                
                process.wait()
                self.after(0, self._log, "Загрузка завершена.")
                
            except Exception as e:
                self.after(0, lambda: self._log(f"Ошибка: {str(e)}"))
            finally:
                self.after(0, self._enable_controls)
                self.after(0, self.refresh_list)

        threading.Thread(target=run, daemon=True).start()

    def _enable_controls(self):
        self.entry_name.config(state=tk.NORMAL)
        self.btn_pull.config(state=tk.NORMAL)
        self.is_busy = False