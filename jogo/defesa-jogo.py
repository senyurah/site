import tkinter as tk
import random
import json
import winsound
from PIL import Image, ImageTk, ImageDraw
import os

# ----------------------------
# Configurações gerais
# ----------------------------
GAME_TIME = 30

CODE_WORDS = [
      "firewall", "malware", "phishing", "exploit", "trojan",
    "payload", "spyware", "keylogger", "rootkit", "sniffer",
    "spoofed", "bruteforce", "ransom", "session", "hashing",
    "sandbox", "backdoor", "scanner", "tracker", "breach",
    "vpnproxy", "forensic", "leakage", "decoder", "Whitehat",
    "threats", "cracked",  "recon", "access","Blackhat",
    "injected", "relogin", "logout",  "cookies","Cracker",
    "tokens", "bypass", "infected", "alerts", "hacker"
]


# Paleta defensiva (azul)
DEF_PRIMARY   = "#0B3D91"   # azul profundo
DEF_SECONDARY = "#4FA3FF"   # azul claro
DEF_ACCENT    = "#BFE8FF"   # acento suave
BG_OVERLAY    = "#00111A"   # camada escura semi-transparente

# Paleta do menu (foco em legibilidade no azul)
MENU_TEXT        = "#E8F7FF"  # texto principal (alto contraste)
MENU_SHADOW      = "#003B73"  # sombra/glow do título
MENU_CARD_BG     = "#001A33"  # cartão central
MENU_ENTRY_BG    = "#04223A"  # campo de entrada
MENU_BTN_BG      = "#0EA5E9"  # botão normal
MENU_BTN_BG_HOV  = "#38BDF8"  # botão hover
MENU_ACCENT_SOFT = "#7FD3FF"  # acento suave

BASE_DIR = os.path.dirname(__file__)
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscore.json")
MENU_BG_CANDIDATES = [
    os.path.join(BASE_DIR, "menu_world_blue.png"),  # recomendado: mapa-múndi azul
    os.path.join(BASE_DIR, "world.png"),            # fallback
]

# ----------------------------
# Classe principal
# ----------------------------
class BaseGame:
    def __init__(self, root, title):
        self.root = root
        self.root.title(title)
        self.root.geometry("1000x700")
        self.root.configure(bg="black")

        # variáveis principais
        self.score = 0
        self.time_left = GAME_TIME
        self.current_code = ""
        self.last_code = ""
        self.letters = []
        self.bg_images = []
        self.paused = False
        self.sound_on = True
        self.matrix_job = None
        self.timer_job = None

        # controle do menu
        self.menu_canvas = None
        self._menu_bg_img = None       # PIL Image
        self._menu_bg_photo = None     # ImageTk.PhotoImage
        self._menu_card_window = None  # id do create_window
        self._menu_resize_bound = False

        # carregar highscore
        self.highscore = self.load_highscore()

        # mostrar tela inicial
        self.show_start_screen()
        self.root.attributes("-fullscreen", True)

    # ----------------------------
    # Start / UI inicial (menu)
    # ----------------------------
    def show_start_screen(self):
        # limpar tudo
        for widget in self.root.winfo_children():
            widget.destroy()

        # Canvas de fundo do menu (permitindo imagem + overlay)
        self.menu_canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.menu_canvas.pack(fill="both", expand=True)

        # carrega e desenha o fundo
        self.load_menu_background()
        self.draw_menu_background()

        # cartão central (colocado dentro do Canvas via create_window)
        card = tk.Frame(
            self.menu_canvas,
            bg=MENU_CARD_BG,
            highlightbackground=DEF_SECONDARY,
            highlightthickness=2,
            padx=24, pady=24
        )
        self._menu_card_window = self.menu_canvas.create_window(
            self.root.winfo_width()//2,
            self.root.winfo_height()//2,
            window=card, anchor="center"
        )

        # TÍTULO com leve glow/sombra para legibilidade
        title_container = tk.Frame(card, bg=MENU_CARD_BG)
        title_container.pack(pady=(0, 10))

        # Canvas interno para sobrepor sombra + texto (melhor que 2 Labels com place)
        title_canvas = tk.Canvas(
            title_container, width=700, height=70,
            bg=MENU_CARD_BG, highlightthickness=0
        )
        title_canvas.pack()
        title_text = "     HACKER CHALLENGE - DEFESA "
        # sombra
        title_canvas.create_text(
            302, 36, text=title_text,
            fill=MENU_SHADOW, font=("Consolas", 36, "bold")
        )
        # texto principal
        title_canvas.create_text(
            300, 34, text=title_text,
            fill=MENU_TEXT, font=("Consolas", 36, "bold")
        )

        # Descrição
        desc = tk.Label(
            card,
            text="Mostre sua habilidade e prove que você é rápido ",
            font=("Consolas", 16),
            fg=MENU_ACCENT_SOFT, bg=MENU_CARD_BG
        )
        desc.pack(pady=(0, 10))

        # Painel de nome (rótulo + entry)
        panel_name = tk.Frame(card, bg=MENU_CARD_BG)
        panel_name.pack(pady=(6, 12))

        lbl = tk.Label(
            panel_name,
            text="Digite seu codinome hacker:",
            font=("Consolas", 16, "bold"),
            fg=MENU_TEXT, bg=MENU_CARD_BG
        )
        lbl.pack(anchor="center")

        self.entry_container = tk.Frame(
            panel_name,
            bg=DEF_PRIMARY,
            highlightbackground=DEF_SECONDARY,
            highlightthickness=2,
            padx=3, pady=3
        )
        self.entry_container.pack(pady=(6, 0))

        self.name_entry = tk.Entry(
            self.entry_container,
            font=("Consolas", 18, "bold"),
            justify="center",
            bg=MENU_ENTRY_BG,
            fg="white",
            insertbackground="white",
            width=26,
            bd=0
        )
        self.name_entry.pack()
        self.name_entry.focus()

        # Botão Iniciar com hover
        start_btn = tk.Button(
            card,
            text="▶ INICIAR JOGO",
            font=("Arial", 16, "bold"),
            bg=MENU_BTN_BG, fg="white",
            activebackground=MENU_BTN_BG_HOV,
            activeforeground="white",
            relief="flat", padx=24, pady=10,
            cursor="hand2",
            command=self.start_game
        )
        start_btn.pack(pady=(16, 8))

        def on_enter_btn(e): start_btn.config(bg=MENU_BTN_BG_HOV)
        def on_leave_btn(e): start_btn.config(bg=MENU_BTN_BG)

        start_btn.bind("<Enter>", on_enter_btn)
        start_btn.bind("<Leave>", on_leave_btn)

        # Highscore e "Pressione ENTER"
        hs_text = f"Recorde: {self.highscore}"
        self.hs_label = tk.Label(
            card, text=hs_text,
            font=("Consolas", 15),
            fg=DEF_ACCENT, bg=MENU_CARD_BG
        )
        self.hs_label.pack(pady=(4, 0))

        self.press_label = tk.Label(
            card, text="Pressione ENTER para começar…",
            font=("Consolas", 16,"bold"),
            fg="#FFD24D", bg=MENU_CARD_BG
        )
        self.press_label.pack(pady=(2, 0))
        self.blink_text(self.press_label)

        # binds para Enter
        self.name_entry.bind("<Return>", lambda e: self.start_game())
        self.root.bind("<Return>", lambda e: self.start_game())

        # Redesenhar o fundo do menu ao redimensionar
        if not self._menu_resize_bound:
            self.menu_canvas.bind("<Configure>", self._on_menu_resize)
            self._menu_resize_bound = True

    # --- Utilidades do menu ---
    def load_menu_background(self):
        """Tenta carregar uma imagem de fundo só para o menu."""
        self._menu_bg_img = None
        for path in MENU_BG_CANDIDATES:
            try:
                if os.path.exists(path):
                    self._menu_bg_img = Image.open(path).convert("RGB")
                    break
            except Exception:
                pass
        if self._menu_bg_img is None:
            # fallback: gradiente azul escuro
            self._menu_bg_img = self._make_fallback_gradient(1000, 700)

    def _make_fallback_gradient(self, w, h):
        """Gera um gradiente sutil azul como fallback."""
        img = Image.new("RGB", (w, h), "#081A30")
        draw = ImageDraw.Draw(img)
        top = (8, 26, 48)
        bot = (3, 12, 28)
        for y in range(h):
            t = y / max(1, h-1)
            r = int(top[0]*(1-t) + bot[0]*t)
            g = int(top[1]*(1-t) + bot[1]*t)
            b = int(top[2]*(1-t) + bot[2]*t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        return img

    def draw_menu_background(self):
        """Desenha a imagem de fundo (cover) + overlay para legibilidade."""
        if not self.menu_canvas or not self._menu_bg_img:
            return
        w = max(1, self.menu_canvas.winfo_width())
        h = max(1, self.menu_canvas.winfo_height())

        # Ajuste tipo "cover": preenche tudo mantendo proporção e cortando sobras
        iw, ih = self._menu_bg_img.size
        scale = max(w / iw, h / ih)
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        img = self._menu_bg_img.resize((nw, nh), Image.LANCZOS)
        # recorte central
        x = max(0, (nw - w) // 2)
        y = max(0, (nh - h) // 2)
        img = img.crop((x, y, x + w, y + h))

        self._menu_bg_photo = ImageTk.PhotoImage(img)
        self.menu_canvas.delete("bg")
        self.menu_canvas.create_image(0, 0, anchor="nw", image=self._menu_bg_photo, tags=("bg",))
        # overlay escuro (stipple para simular transparência)
        self.menu_canvas.create_rectangle(0, 0, w, h, fill=BG_OVERLAY, stipple="gray25", width=0, tags=("bg",))

        # Reposicionar a janela do cartão no centro atual
        if self._menu_card_window:
            self.menu_canvas.coords(self._menu_card_window, w//2, h//2)

    def _on_menu_resize(self, event):
        # redesenha o fundo quando o canvas muda de tamanho
        self.draw_menu_background()

    # ----------------------------
    # Reset do jogo
    # ----------------------------
    def reset_game(self):
        if self.matrix_job:
            try:
                self.root.after_cancel(self.matrix_job)
            except Exception:
                pass
            self.matrix_job = None
        if self.timer_job:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

        for w in self.root.winfo_children():
            w.destroy()
        self.score = 0
        self.time_left = GAME_TIME
        self.current_code = ""
        self.last_code = ""
        self.letters = []
        self.bg_images = []
        self.paused = False
        self.sound_on = True
        self.matrix_job = None
        self.timer_job = None
        self.show_start_screen()

    def blink_text(self, widget):
        cur = widget.cget("fg")
        nxt = "black" if cur != "black" else "#FFD24D"
        widget.config(fg=nxt)
        self.root.after(700, lambda: self.blink_text(widget))

    # ----------------------------
    # Game start
    # ----------------------------
    def start_game(self):
        # limpar binds do menu
        try:
            self.root.unbind("<Return>")
        except Exception:
            pass

        self.player_name = getattr(self, "name_entry", None)
        if self.player_name:
            self.player_name = self.name_entry.get().strip() or "Anônimo"
        else:
            self.player_name = "Anônimo"

        # destruir o menu
        if self.menu_canvas:
            try:
                self.menu_canvas.unbind("<Configure>")
            except Exception:
                pass
            try:
                self.menu_canvas.destroy()
            except Exception:
                pass
            self.menu_canvas = None

        # criar área do jogo
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.load_background_images()
        self.draw_background_layers()

        self.top_panel = tk.Frame(self.root, bg="#021324", highlightthickness=0)
        self.top_panel.place(relx=0.5, y=14, anchor="n", width=920, height=64)

        self.score_label = tk.Label(
            self.top_panel,
            text=f"Pontuação: {self.score}",
            font=("Consolas", 18, "bold"),
            fg=DEF_ACCENT,
            bg="#021324"
        )
        self.score_label.pack(side="left", padx=28)

        self.high_label = tk.Label(
            self.top_panel,
            text=f"Highscore: {self.highscore}",
            font=("Consolas", 12, "bold"),
            fg=DEF_ACCENT,
            bg="#021324"
        )
        self.high_label.pack(side="left", padx=10)

        self.time_label = tk.Label(
            self.top_panel,
            text=f"⏳ Tempo: {self.time_left}s",
            font=("Consolas", 18, "bold"),
            fg="red",
            bg="#021324"
        )
        self.time_label.pack(side="right", padx=28)

        self.time_bar = tk.Canvas(self.root, width=920, height=10, bg="red", highlightthickness=0)
        self.time_bar.place(relx=0.5, y=84, anchor="n")

        self.code_panel = tk.Frame(self.root, bg="#001427", highlightbackground=DEF_PRIMARY, highlightthickness=3)
        self.code_panel.place(relx=0.5, rely=0.35, anchor="center")

        self.code_label = tk.Label(
            self.code_panel,
            text="",
            font=("Consolas", 34, "bold"),
            fg=DEF_SECONDARY,
            bg="#001427"
        )
        self.code_label.pack(padx=20, pady=10)

        self.entry_frame = tk.Frame(self.root, bg="#001427", highlightbackground=DEF_PRIMARY, highlightthickness=3)
        self.entry_frame.place(relx=0.5, rely=0.55, anchor="center")

        self.entry = tk.Entry(
            self.entry_frame,
            font=("Consolas", 22, "bold"),
            justify="center",
            bg="#021324",
            fg=DEF_ACCENT,
            insertbackground=DEF_ACCENT,
            bd=0,
            width=28
        )
        self.entry.pack(ipady=10, ipadx=18)
        self.entry.bind("<Return>", self.check_word)
        self.entry.focus()

        self.draw_decorations()

        self.new_code()
        self.update_timer()
        self.create_matrix()
        self.animate_matrix()

    # ----------------------------
    # Background images (do JOGO)
    # ----------------------------
    def load_background_images(self):
        base_dir = BASE_DIR
        try:
            world = Image.open(os.path.join(base_dir, "world.png"))
        except Exception:
            world = None
        try:
            texture = Image.open(os.path.join(base_dir, "texture.png"))
        except Exception:
            texture = None

        self.bg_images = [img for img in (world, texture) if img is not None]

    def draw_background_layers(self):
        w = max(1, self.root.winfo_width())
        h = max(1, self.root.winfo_height())
        self.canvas.delete("bglayer")
        if self.bg_images:
            for i, img in enumerate(self.bg_images):
                try:
                    im = img.resize((w, h), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(im)
                    setattr(self, f"_bg_photo_{i}", photo)  # evitar GC
                    self.canvas.create_image(0, 0, anchor="nw", image=photo, tags=("bglayer",))
                except Exception:
                    pass
            # overlay levemente escuro
            self.canvas.create_rectangle(0, 0, w, h, fill=BG_OVERLAY, stipple="gray50", tags=("bglayer",))
        else:
            self.canvas.create_rectangle(0, 0, w, h, fill="#001022", tags=("bglayer",))

    # ----------------------------
    # Decorações
    # ----------------------------
    def draw_decorations(self):
        w = self.root.winfo_width() or 1000
        x = w - 120
        
    # ----------------------------
    # Lógica do jogo
    # ----------------------------
    def new_code(self):
        self.current_code = random.choice(CODE_WORDS)
        while self.current_code == self.last_code:
            self.current_code = random.choice(CODE_WORDS)
        self.last_code = self.current_code
        self.code_label.config(text=self.current_code)
        try:
            self.entry.delete(0, "end")
        except Exception:
            pass

    def pulse_target(self, color="#4FA3FF"):
        panel = getattr(self, "code_panel", None)
        if panel is None:
            return

        def step(n):
            if n <= 0:
                panel.config(highlightthickness=3, highlightbackground=DEF_PRIMARY)
                return
            panel.config(highlightthickness=6, highlightbackground=color)
            self.root.after(100, lambda: (panel.config(highlightthickness=3, highlightbackground=DEF_PRIMARY), step(n-1)))
        step(2)

    def play_sound(self, ok=True):
        if not getattr(self, "sound_on", True):
            return
        try:
            if ok:
                winsound.Beep(1000, 120)
            else:
                winsound.Beep(400, 300)
        except Exception:
            pass

    def check_word(self, event=None):
        typed = self.entry.get().strip()
        if typed == self.current_code:
            self.score += 10
            self.score_label.config(text=f"Pontuação: {self.score}")
            self.play_sound(ok=True)
            self.pulse_target('#00FFAA')
            self.new_code()
        else:
            self.score = max(0, self.score - 5)
            self.score_label.config(text=f"Pontuação: {self.score}")
            self.play_sound(ok=False)
            self.pulse_target('#FF0044')
        try:
            self.entry.delete(0, "end")
        except Exception:
            pass

    # ----------------------------
    # Timer & Game Over
    # ----------------------------
    def update_timer(self):
        if self.timer_job:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

        if self.paused:
            self.timer_job = self.root.after(500, self.update_timer)
            return

        if self.time_left > 0:
            self.time_left -= 1
            self.time_label.config(text=f"⏳ Tempo: {self.time_left}s")
            try:
                width = int(920 * self.time_left / GAME_TIME)
                self.time_bar.config(width=max(0, width))
            except Exception:
                pass
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.game_over()

    def game_over(self):
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore(self.highscore)
        self.show_game_over_screen()

    def show_game_over_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg="black")
        frame.pack(expand=True)

        tk.Label(frame, text="☠️ FIM DE JOGO ☠️", fg="red", bg="black", font=("Consolas", 28, "bold")).pack(pady=20)
        tk.Label(frame, text=f"Pontuação Final: {self.score}", fg="white", bg="black", font=("Consolas", 22)).pack(pady=10)
        tk.Label(frame, text=f"Recorde: {self.highscore}", fg="yellow", bg="black", font=("Consolas", 20)).pack(pady=10)

        self.root.bind("9", lambda event: self.restart_game())

    def restart_game(self):
        self.root.unbind("9")
        self.score = 0
        self.time_left = GAME_TIME
        self.current_code = ""
        self.last_code = ""
        self.letters = []

        self.menu_canvas = None
        self._menu_bg_img = None
        self._menu_bg_photo = None
        self._menu_card_window = None
        self._menu_resize_bound = False

        self.show_start_screen()

    # ----------------------------
    # Efeito "Matrix"
    # ----------------------------
    def create_matrix(self):
        self.canvas.delete("matrix")
        self.letters = []
        width = max(1, self.root.winfo_width())
        height = max(1, self.root.winfo_height())
        for _ in range(220):
            x = random.randint(0, width)
            y = random.randint(-height, 0)
            digit = random.choice(["0", "1"])
            color = random.choice([DEF_PRIMARY, DEF_SECONDARY, DEF_ACCENT])
            text_id = self.canvas.create_text(x, y, text=digit, fill=color, font=("Consolas", 12, "bold"), tags=("matrix",))
            self.letters.append((text_id, random.randint(2, 6)))

    def animate_matrix(self):
        width = max(1, self.root.winfo_width())
        height = max(1, self.root.winfo_height())
        for text_id, speed in list(self.letters):
            try:
                self.canvas.move(text_id, 0, speed)
                coords = self.canvas.coords(text_id)
                if not coords:
                    continue
                x, y = coords
                if y > height:
                    self.canvas.coords(text_id, x, -10)
                    self.canvas.itemconfig(text_id, text=random.choice(["0", "1"]), fill=random.choice([DEF_PRIMARY, DEF_SECONDARY, DEF_ACCENT]))
            except Exception:
                pass

        if self.matrix_job:
            try:
                self.root.after_cancel(self.matrix_job)
            except Exception:
                pass
        self.matrix_job = self.root.after(50, self.animate_matrix)

    # ----------------------------
    # Highscore persistência
    # ----------------------------
    def load_highscore(self):
        try:
            if os.path.exists(HIGHSCORE_FILE):
                with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return int(data.get("highscore", 0))
        except Exception:
            pass
        return 0

    def save_highscore(self, score):
        try:
            with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
                json.dump({"highscore": int(score)}, f)
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    game = BaseGame(root, "🛡️ Hacker Challenge - Defesa 🛡️")
    root.mainloop()
        