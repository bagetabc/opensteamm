import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import os
import json
import threading
from pathlib import Path
import platform
import requests
from datetime import datetime
import shutil

class ManifestGenerator:
    """Генератор манифестов"""
    
    def __init__(self, gui_callback=None):
        self.base_dir = Path(sys.argv[0]).parent.absolute()
        self.storage_dir = self.base_dir / "storage"
        self.logs_dir = self.base_dir / "logs"
        self.config_file = self.base_dir / "config" / "settings.json"
        self.gui_callback = gui_callback
        
        self.steam_tools_path = None
        
        self.ensure_directories()
        self.load_config()
        self.find_steam_tools()
    
    def log(self, message, level="info"):
        if self.gui_callback:
            self.gui_callback(message, level)
    
    def ensure_directories(self):
        for folder in [self.storage_dir, self.logs_dir, self.config_file.parent]:
            folder.mkdir(parents=True, exist_ok=True)
    
    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {"steam_tools_path": ""}
                self.save_config()
        except:
            self.config = {}
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except:
            pass
    
    def find_steam_tools(self):
        """Ищет Steam Tools на компьютере"""
        if self.config.get("steam_tools_path"):
            path = Path(self.config["steam_tools_path"])
            if path.exists():
                self.steam_tools_path = path
                return True
        
        possible_paths = [
            Path(os.environ.get('LOCALAPPDATA', '')) / "SteamTools",
            Path.home() / "AppData" / "Local" / "SteamTools",
            Path.home() / "AppData" / "Roaming" / "SteamTools",
            Path("C:\\Program Files\\SteamTools"),
        ]
        
        for path in possible_paths:
            if path.exists():
                self.steam_tools_path = path
                self.config["steam_tools_path"] = str(path)
                self.save_config()
                return True
        
        return False
    
    def get_game_info(self, app_id):
        """Получает информацию об игре"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if str(app_id) in data and data[str(app_id)]['success']:
                return data[str(app_id)]['data']['name']
            return f"Game_{app_id}"
        except:
            return f"Game_{app_id}"
    
    def generate_lua(self, app_id, game_name):
        """Генерирует Lua скрипт"""
        return f'''-- OpenSteamM Generated Lua Script
-- AppID: {app_id}
-- Game: {game_name}
-- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

local manifest = {{
    ["appid"] = {app_id},
    ["name"] = "{game_name}",
    ["manifest"] = "manifest_{app_id}.st",
    ["lua"] = true
}}

function UnlockGame()
    Steam.apps.setAppBuildId({app_id}, 0)
    print("[OpenSteamM] Game unlocked: " .. "{game_name}")
end

UnlockGame()
return manifest
'''
    
    def generate_manifest(self, app_id, game_name):
        """Генерирует st манифест"""
        return json.dumps({
            "appid": int(app_id),
            "name": game_name,
            "generated_by": "OpenSteamM",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "depots": {"1": {"manifest": "0"}},
            "dlcs": []
        }, indent=4, ensure_ascii=False)
    
    def copy_to_steamtools(self, app_id):
        """Копирует файлы в Steam Tools"""
        if not self.steam_tools_path:
            return False
        
        manifests_dir = self.steam_tools_path / "Manifests"
        manifests_dir.mkdir(exist_ok=True)
        
        app_folder = self.storage_dir / app_id
        lua_file = app_folder / f"manifest_{app_id}.lua"
        st_file = app_folder / f"manifest_{app_id}.st"
        
        if not lua_file.exists() or not st_file.exists():
            return False
        
        shutil.copy2(lua_file, manifests_dir / f"manifest_{app_id}.lua")
        shutil.copy2(st_file, manifests_dir / f"manifest_{app_id}.st")
        return True
    
    def generate(self, app_id):
        """Генерация"""
        self.log(f"Генерация для APP ID: {app_id}")
        
        app_folder = self.storage_dir / app_id
        app_folder.mkdir(parents=True, exist_ok=True)
        
        game_name = self.get_game_info(app_id)
        self.log(f"Игра: {game_name}", "success")
        
        lua_path = app_folder / f"manifest_{app_id}.lua"
        with open(lua_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_lua(app_id, game_name))
        self.log(f"✅ Lua: {lua_path}", "success")
        
        st_path = app_folder / f"manifest_{app_id}.st"
        with open(st_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_manifest(app_id, game_name))
        self.log(f"✅ Манифест: {st_path}", "success")
        
        if self.steam_tools_path:
            self.copy_to_steamtools(app_id)
            self.log(f"✅ Скопировано в Steam Tools", "success")
        
        return True
    
    def get_saved_apps(self):
        apps = []
        if self.storage_dir.exists():
            for item in self.storage_dir.iterdir():
                if item.is_dir() and item.name.isdigit():
                    lua = item / f"manifest_{item.name}.lua"
                    st = item / f"manifest_{item.name}.st"
                    if lua.exists() and st.exists():
                        apps.append(item.name)
        return sorted(apps)


class OpenSteamMGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OpenSteamM - Steam Tools Manager")
        self.root.geometry("950x750")
        self.root.minsize(850, 650)
        self.root.configure(bg='#1a1a2e')
        
        self.app_id_var = tk.StringVar(value="730")
        self.status_var = tk.StringVar(value="Готов к работе")
        
        # Сначала создаем UI
        self.setup_ui()
        
        # Потом создаем генератор (после того как log_text существует)
        self.generator = ManifestGenerator(gui_callback=self.add_log)
        
        # Обновляем статус
        self.update_steam_tools_status()
        self.load_saved_apps()
        
        self.add_log("OpenSteamM запущен", "success")
    
    def setup_ui(self):
        main = tk.Frame(self.root, bg='#1a1a2e')
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Заголовок
        title = tk.Label(main, text="⚙️ OPENSTEAMM", 
                        font=('Segoe UI', 24, 'bold'),
                        fg='#6c8bd6', bg='#1a1a2e')
        title.pack(pady=(0, 5))
        
        subtitle = tk.Label(main, text="Генератор манифестов для Steam Tools",
                           font=('Segoe UI', 10),
                           fg='#8888aa', bg='#1a1a2e')
        subtitle.pack(pady=(0, 20))
        
        # Статус Steam Tools
        status_frame = tk.LabelFrame(main, text=" 🔧 Статус Steam Tools ",
                                     bg='#1e1e2e', fg='#ffd700',
                                     font=('Segoe UI', 10, 'bold'))
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_row = tk.Frame(status_frame, bg='#1e1e2e')
        status_row.pack(fill=tk.X, padx=10, pady=10)
        
        self.steam_tools_status = tk.Label(status_row, text="❌ Не найден",
                                          bg='#1e1e2e', fg='#e74c3c')
        self.steam_tools_status.pack(side=tk.LEFT)
        
        tk.Button(status_row, text="📂 Указать путь", command=self.set_steam_tools_path,
                 bg='#2c3147', fg='#fff', relief=tk.FLAT, padx=10).pack(side=tk.RIGHT)
        
        # Генерация
        gen_frame = tk.LabelFrame(main, text=" 🚀 Генерация ",
                                  bg='#1e1e2e', fg='#4c6ef5',
                                  font=('Segoe UI', 10, 'bold'))
        gen_frame.pack(fill=tk.X, pady=(0, 15))
        
        gen_row = tk.Frame(gen_frame, bg='#1e1e2e')
        gen_row.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(gen_row, text="APP ID:", bg='#1e1e2e', fg='#ccc').pack(side=tk.LEFT, padx=(0, 10))
        
        self.appid_entry = tk.Entry(gen_row, textvariable=self.app_id_var,
                                    font=('Consolas', 14), width=12,
                                    bg='#0f0f1a', fg='#fff', relief=tk.FLAT)
        self.appid_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Button(gen_row, text="🚀 Сгенерировать", command=self.generate_manifest,
                 bg='#4c6ef5', fg='#fff', font=('Segoe UI', 11, 'bold'),
                 relief=tk.FLAT, padx=20, pady=8).pack(side=tk.LEFT)
        
        # Список сохраненных
        saved_frame = tk.LabelFrame(main, text=" 📁 Сохраненные ",
                                   bg='#1e1e2e', fg='#6fcf97',
                                   font=('Segoe UI', 10, 'bold'))
        saved_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.saved_listbox = tk.Listbox(saved_frame, bg='#0a0e18', fg='#6fcf97',
                                        font=('Consolas', 10), height=5,
                                        relief=tk.FLAT)
        self.saved_listbox.pack(fill=tk.X, padx=10, pady=10)
        
        btn_row = tk.Frame(saved_frame, bg='#1e1e2e')
        btn_row.pack(pady=(0, 10))
        
        tk.Button(btn_row, text="📂 Открыть папку", command=self.open_app_folder,
                 bg='#2c3147', fg='#fff', relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_row, text="📋 В Steam Tools", command=self.copy_to_steamtools,
                 bg='#4c6ef5', fg='#fff', relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_row, text="🗑️ Удалить", command=self.delete_app,
                 bg='#e74c3c', fg='#fff', relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=5)
        
        # Логи
        log_frame = tk.LabelFrame(main, text=" 📝 Логи ",
                                  bg='#1e1e2e', fg='#5dade2',
                                  font=('Segoe UI', 10, 'bold'))
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, bg='#0a0e18', fg='#5dade2',
                                font=('Consolas', 9), relief=tk.FLAT, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scroll = tk.Scrollbar(self.log_text, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scroll.set)
        
        self.log_text.tag_config('info', foreground='#5dade2')
        self.log_text.tag_config('success', foreground='#6fcf97')
        self.log_text.tag_config('warning', foreground='#f1c40f')
        self.log_text.tag_config('error', foreground='#e74c3c')
        
        # Статусбар
        status = tk.Label(self.root, textvariable=self.status_var,
                         bg='#0f0f1a', fg='#8888aa', font=('Segoe UI', 9))
        status.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.appid_entry.bind('<Return>', lambda e: self.generate_manifest())
    
    def update_steam_tools_status(self):
        if self.generator and self.generator.steam_tools_path:
            self.steam_tools_status.config(text=f"✅ Steam Tools: {self.generator.steam_tools_path}", fg='#6fcf97')
        else:
            self.steam_tools_status.config(text="❌ Steam Tools не найден", fg='#e74c3c')
    
    def set_steam_tools_path(self):
        folder = filedialog.askdirectory(title="Выберите папку Steam Tools")
        if folder:
            self.generator.steam_tools_path = Path(folder)
            self.generator.config["steam_tools_path"] = folder
            self.generator.save_config()
            self.update_steam_tools_status()
            self.add_log(f"Путь сохранен: {folder}", "success")
    
    def add_log(self, message, level="info"):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            self.log_text.insert(tk.END, f"[{ts}] {message}\n", level)
            self.log_text.see(tk.END)
        except:
            pass
        
        if level == "error":
            self.status_var.set(f"Ошибка")
        elif level == "success":
            self.status_var.set(f"Успешно")
        else:
            self.status_var.set(f"Готов")
        
        self.root.update_idletasks()
    
    def load_saved_apps(self):
        self.saved_listbox.delete(0, tk.END)
        for app in self.generator.get_saved_apps():
            self.saved_listbox.insert(tk.END, f"✅  APP ID: {app}")
    
    def generate_manifest(self):
        app_id = self.app_id_var.get().strip()
        if not app_id:
            self.add_log("Введите APP ID", "error")
            return
        
        if not app_id.isdigit():
            self.add_log("APP ID только цифры", "error")
            return
        
        self.add_log(f"Генерация для APP ID: {app_id}", "info")
        
        def gen_thread():
            result = self.generator.generate(app_id)
            self.load_saved_apps()
            self.update_steam_tools_status()
            if result:
                self.add_log(f"✅ Готово! storage/{app_id}/", "success")
            else:
                self.add_log(f"❌ Ошибка", "error")
        
        threading.Thread(target=gen_thread, daemon=True).start()
    
    def copy_to_steamtools(self):
        sel = self.saved_listbox.curselection()
        if not sel:
            self.add_log("Выберите приложение", "warning")
            return
        
        text = self.saved_listbox.get(sel[0])
        app_id = text.split("APP ID:")[-1].strip()
        
        if self.generator.copy_to_steamtools(app_id):
            self.add_log(f"✅ Скопировано в Steam Tools", "success")
            self.add_log(f"💡 Нажмите F9 и перезапустите Steam", "info")
        else:
            self.add_log(f"❌ Ошибка копирования", "error")
    
    def open_app_folder(self):
        sel = self.saved_listbox.curselection()
        if not sel:
            self.add_log("Выберите приложение", "warning")
            return
        
        text = self.saved_listbox.get(sel[0])
        app_id = text.split("APP ID:")[-1].strip()
        folder = Path(f"storage/{app_id}")
        
        if folder.exists():
            if platform.system() == "Windows":
                os.startfile(folder)
            self.add_log(f"Открыта папка: {folder}", "success")
    
    def delete_app(self):
        sel = self.saved_listbox.curselection()
        if not sel:
            self.add_log("Выберите приложение", "warning")
            return
        
        text = self.saved_listbox.get(sel[0])
        app_id = text.split("APP ID:")[-1].strip()
        
        if messagebox.askyesno("Подтверждение", f"Удалить APP ID {app_id}?"):
            folder = Path(f"storage/{app_id}")
            if folder.exists():
                shutil.rmtree(folder)
                self.add_log(f"Удалено: {folder}", "success")
                self.load_saved_apps()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = OpenSteamMGUI()
    app.run()