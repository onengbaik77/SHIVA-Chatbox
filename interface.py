import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import re

from brain.manager import BrainManager
from core.shiva_network import check_connection

from brain.history.history import (
    create_chat,
    add_message,
    get_chat,
    get_all_chats,
    rename_chat,
    delete_chat,
)

from core.llm import check_ollama_status
from memory_center import MemoryCenter
from capabilities_center import CapabilitiesCenter
from project_center import ProjectCenter
from shiva_security_window import ShivaSecurityWindow
from core.shiva_security_runtime import ShivaSecurityRuntime


from core.project_plan_lock import ProjectPlanLock
from core.preview_controller import PreviewController

class ShivaInterface:

    def toggle_online_mode(self):
        self.online_mode = not self.online_mode

        if self.online_mode:
            connection = check_connection()

            if connection.get("online"):
                self.brain.network_online = True
                self.online_toggle.configure(
                    text="🌐 ONLINE",
                    fg=self.online_color,
                    activeforeground=self.online_color
                )
            else:
                self.online_mode = False
                self.brain.network_online = False
                self.online_toggle.configure(
                    text="🌐 OFFLINE",
                    fg=self.offline_color,
                    activeforeground=self.offline_color
                )
        else:
            self.brain.network_online = False
            self.online_toggle.configure(
                text="🌐 OFFLINE",
                fg=self.offline_color,
                activeforeground=self.offline_color
            )

    def __init__(self, root):
        self.root = root

        # ==========================================
        # WINDOW
        # ==========================================
        self.root.title("SHIVA ORIGIN v0.1 by Yuwwa")
        self.root.geometry("1150x720")
        self.root.minsize(900, 560)

        # Start SHIVA maximized on Windows
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass

        # ==========================================
        # SHIVA BRAIN
        # ==========================================
        self.brain = BrainManager()
        self.preview_controller = PreviewController()
        self.security_runtime = ShivaSecurityRuntime()

        self.response_queue = queue.Queue()
        self.status_queue = queue.Queue()

        self.current_chat_id = None
        self.streaming_answer = ""
        self.is_generating = False
        self.status_check_running = False

        # ==========================================
        # STREAMING UI OPTIMIZATION
        # ==========================================
        self.stream_render_pending = False
        self.stream_render_after_id = None

        # ==========================================
        # NETWORK MODE
        # ==========================================
        self.online_mode = False

        # ==========================================
        # COLORS
        # ==========================================
        self.bg = "#0B0B0B"
        self.panel = "#151515"
        self.sidebar_bg = "#101010"
        self.input_bg = "#202020"
        self.button_bg = "#1C1C1C"
        self.active_bg = "#292929"

        self.text_color = "#F2F2F2"
        self.secondary_text = "#8B8B8B"

        self.online_color = "#74C991"
        self.offline_color = "#D66B6B"
        self.warning_color = "#D6B66B"

        self.root.configure(bg=self.bg)

        # ==========================================
        # MAIN GRID
        # ==========================================
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(
            0,
            weight=0,
            minsize=240
        )
        self.root.grid_columnconfigure(
            1,
            weight=1
        )

        # ==========================================
        # SIDEBAR
        # ==========================================
        self.sidebar = tk.Frame(
            self.root,
            bg=self.sidebar_bg,
            width=240
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.sidebar.grid_propagate(False)

        # ==========================================
        # BRAND
        # ==========================================
        logo = tk.Label(
            self.sidebar,
            text="SHIVA",
            font=("Segoe UI", 22, "bold"),
            fg=self.text_color,
            bg=self.sidebar_bg
        )

        logo.pack(
            anchor="w",
            padx=22,
            pady=(25, 0)
        )

        origin = tk.Label(
            self.sidebar,
            text="ORIGIN v0.1  by Yuwwa",
            font=("Segoe UI", 9),
            fg=self.secondary_text,
            bg=self.sidebar_bg
        )

        origin.pack(
            anchor="w",
            padx=23,
            pady=(0, 22)
        )

        # ==========================================
        # NEW CHAT
        # ==========================================
        self.new_chat_button = tk.Button(
            self.sidebar,
            text="+  New Chat",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#000000",
            activebackground="#DDDDDD",
            activeforeground="#000000",
            relief="flat",
            cursor="hand2",
            command=self.new_chat
        )

        self.new_chat_button.pack(
            fill="x",
            padx=15,
            pady=(0, 20),
            ipady=8
        )

        # ==========================================
        # SIDEBAR MENU
        # ==========================================
        self.make_sidebar_button(
            "Chat",
            bold=True
        )

        self.make_sidebar_button(
            "Memory",
            command=self.show_memory_info
        )

        self.make_sidebar_button(
            "Capabilities",
            command=self.show_capabilities
        )

        self.make_sidebar_button(
            "Projects",
            command=self.show_projects
        )

        self.make_sidebar_button(
            "🛡 Security",
            command=self.show_security
        )

        # ==========================================
        # HISTORY
        # ==========================================
        history_label = tk.Label(
            self.sidebar,
            text="CHAT HISTORY",
            font=("Segoe UI", 8, "bold"),
            fg="#666666",
            bg=self.sidebar_bg
        )

        history_label.pack(
            anchor="w",
            padx=20,
            pady=(22, 8)
        )

        self.history_container = tk.Frame(
            self.sidebar,
            bg=self.sidebar_bg
        )

        self.history_container.pack(
            fill="x",
            padx=10
        )

        self.history_canvas = tk.Canvas(
            self.history_container,
            bg=self.sidebar_bg,
            highlightthickness=0,
            borderwidth=0
        )

        self.history_scrollbar = tk.Scrollbar(
            self.history_container,
            orient="vertical",
            command=self.history_canvas.yview
        )

        self.history_frame = tk.Frame(
            self.history_canvas,
            bg=self.sidebar_bg
        )

        self.history_window = self.history_canvas.create_window(
            (0, 0),
            window=self.history_frame,
            anchor="nw"
        )

        self.history_frame.bind(
            "<Configure>",
            lambda event: self.history_canvas.configure(
                scrollregion=self.history_canvas.bbox("all")
            )
        )

        self.history_canvas.configure(
            yscrollcommand=self.history_scrollbar.set
        )

        self.history_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.history_scrollbar.pack(
            side="right",
            fill="y"
        )

        # ==========================================
        # SIDEBAR BOTTOM
        # ==========================================
        bottom = tk.Frame(
            self.sidebar,
            bg=self.sidebar_bg
        )

        bottom.pack(
            side="bottom",
            fill="x",
            padx=20,
            pady=20
        )

        self.sidebar_status = tk.Label(
            bottom,
            text="● CHECKING...",
            font=("Segoe UI", 9),
            fg=self.secondary_text,
            bg=self.sidebar_bg
        )

        self.sidebar_status.pack(
            anchor="w"
        )

        creator = tk.Label(
            bottom,
            text="SHIVA ORIGIN v0.1 by Yuwwa",
            font=("Segoe UI", 8),
            fg="#555555",
            bg=self.sidebar_bg
        )

        creator.pack(
            anchor="w",
            pady=(5, 0)
        )

        # ==========================================
        # MAIN AREA
        # ==========================================
        self.main = tk.Frame(
            self.root,
            bg=self.bg
        )

        self.main.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.main.grid_rowconfigure(0, weight=0)
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_rowconfigure(2, weight=0)

        self.main.grid_columnconfigure(
            0,
            weight=1,
            minsize=420
        )

        self.main.grid_columnconfigure(
            1,
            weight=1,
            minsize=420
        )

        # ==========================================
        # HEADER
        # ==========================================
        header = tk.Frame(
            self.main,
            bg=self.panel,
            height=75
        )

        header.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew"
        )

        header.grid_propagate(False)

        self.header_title = tk.Label(
            header,
            text="SHIVA ORIGIN",
            font=("Segoe UI", 15, "bold"),
            fg=self.text_color,
            bg=self.panel
        )

        self.header_title.pack(
            side="left",
            padx=25,
            pady=22
        )

        self.online_toggle = tk.Button(
            header,
            text="🌐 OFFLINE",
            font=("Segoe UI", 9, "bold"),
            bg="#202020",
            fg=self.offline_color,
            activebackground="#303030",
            activeforeground=self.offline_color,
            relief="flat",
            cursor="hand2",
            command=self.toggle_online_mode,
            padx=10
        )

        self.online_toggle.pack(
            side="right",
            padx=(5, 20),
            pady=20
        )

        self.header_status = tk.Label(
            header,
            text="● CHECKING...",
            font=("Segoe UI", 9, "bold"),
            fg=self.secondary_text,
            bg=self.panel
        )

        self.header_status.pack(
            side="right",
            padx=25
        )

        # ==========================================
        # CHAT AREA
        # ==========================================
        chat_container = tk.Frame(
            self.main,
            bg=self.bg
        )

        chat_container.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(25, 10),
            pady=15
        )

        chat_container.grid_rowconfigure(
            0,
            weight=1
        )

        chat_container.grid_columnconfigure(
            0,
            weight=1
        )

        self.chat = scrolledtext.ScrolledText(
            chat_container,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg=self.bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief="flat",
            borderwidth=0,
            padx=15,
            pady=15,
            spacing1=2,
            spacing3=3
        )

        self.chat.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # ==========================================
        # LIVE PREVIEW FOUNDATION
        # ==========================================
        self.preview_container = tk.Frame(
            self.main,
            bg=self.panel,
            highlightthickness=1,
            highlightbackground="#2A2A2A"
        )

        self.preview_container.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(10, 25),
            pady=15
        )

        self.preview_container.grid_rowconfigure(
            1,
            weight=1
        )

        self.preview_container.grid_columnconfigure(
            0,
            weight=1
        )

        preview_header = tk.Frame(
            self.preview_container,
            bg=self.panel,
            height=48
        )

        preview_header.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        preview_header.grid_propagate(
            False
        )

        self.preview_title = tk.Label(
            preview_header,
            text="LIVE PREVIEW",
            font=("Segoe UI", 10, "bold"),
            bg=self.panel,
            fg=self.text_color
        )

        self.preview_title.pack(
            side="left",
            padx=16,
            pady=14
        )

        self.preview_status = tk.Label(
            preview_header,
            text="READY",
            font=("Segoe UI", 8, "bold"),
            bg=self.panel,
            fg=self.secondary_text
        )

        self.preview_status.pack(
            side="right",
            padx=(8, 16)
        )

        self.preview_close_button = tk.Button(
            preview_header,
            text="Close",
            font=("Segoe UI", 8, "bold"),
            bg="#202020",
            fg="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.close_live_preview,
            padx=8
        )

        self.preview_close_button.pack(
            side="right",
            padx=3,
            pady=10
        )

        self.preview_refresh_button = tk.Button(
            preview_header,
            text="Refresh",
            font=("Segoe UI", 8, "bold"),
            bg="#202020",
            fg="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.refresh_live_preview,
            padx=8
        )

        self.preview_refresh_button.pack(
            side="right",
            padx=3,
            pady=10
        )

        self.preview_open_button = tk.Button(
            preview_header,
            text="Open",
            font=("Segoe UI", 8, "bold"),
            bg="#202020",
            fg="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            relief="flat",
            cursor="hand2",
            command=self.open_live_preview,
            padx=8
        )

        self.preview_open_button.pack(
            side="right",
            padx=3,
            pady=10
        )

        self.preview_surface = tk.Frame(
            self.preview_container,
            bg="#111111"
        )

        self.preview_surface.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=1,
            pady=(0, 1)
        )

        preview_placeholder = tk.Frame(
            self.preview_surface,
            bg="#111111"
        )

        preview_placeholder.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        self.preview_placeholder_title = tk.Label(
            preview_placeholder,
            text="SHIVA Website Preview",
            font=("Segoe UI", 15, "bold"),
            bg="#111111",
            fg="#FFFFFF"
        )

        self.preview_placeholder_title.pack(
            pady=(0, 8)
        )

        self.preview_placeholder_text = tk.Label(
            preview_placeholder,
            text="Live renderer will appear here.",
            font=("Segoe UI", 10),
            bg="#111111",
            fg="#888888"
        )

        self.preview_placeholder_text.pack()

        # ==========================================
        # TEXT STYLES
        # ==========================================
        self.chat.tag_config(
            "name",
            foreground="#FFFFFF",
            font=("Segoe UI", 11, "bold")
        )

        self.chat.tag_config(
            "message",
            foreground="#D0D0D0",
            font=("Segoe UI", 11)
        )

        self.chat.tag_config(
            "bold",
            foreground="#F5F5F5",
            font=("Segoe UI", 11, "bold")
        )

        self.chat.tag_config(
            "heading1",
            foreground="#FFFFFF",
            font=("Segoe UI", 17, "bold"),
            spacing1=8,
            spacing3=5
        )

        self.chat.tag_config(
            "heading2",
            foreground="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
            spacing1=7,
            spacing3=4
        )

        self.chat.tag_config(
            "heading3",
            foreground="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            spacing1=5,
            spacing3=3
        )

        self.chat.tag_config(
            "bullet",
            foreground="#D0D0D0",
            font=("Segoe UI", 11),
            lmargin1=15,
            lmargin2=30
        )

        self.chat.tag_config(
            "code",
            foreground="#E0E0E0",
            background="#1B1B1B",
            font=("Consolas", 10)
        )

        self.chat.tag_config(
            "quote",
            foreground="#AAAAAA",
            font=("Segoe UI", 11, "italic"),
            lmargin1=20,
            lmargin2=20
        )

        self.chat.tag_config(
            "system",
            foreground="#777777",
            font=("Segoe UI", 9)
        )

        self.chat.configure(
            state="disabled"
        )

        # ==========================================
        # INPUT AREA
        # ==========================================
        input_outer = tk.Frame(
            self.main,
            bg=self.bg
        )

        input_outer.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=30,
            pady=(0, 25)
        )

        input_outer.grid_columnconfigure(
            0,
            weight=1
        )

        input_container = tk.Frame(
            input_outer,
            bg=self.input_bg,
            height=70
        )

        input_container.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        input_container.grid_columnconfigure(
            0,
            weight=1
        )

        self.entry = tk.Entry(
            input_container,
            font=("Segoe UI", 12),
            bg=self.input_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief="flat",
            bd=0
        )

        self.entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(20, 10),
            pady=18,
            ipady=5
        )

        self.entry.bind(
            "<Return>",
            self.send_message
        )

        self.send_button = tk.Button(
            input_container,
            text="Send",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#000000",
            activebackground="#DDDDDD",
            activeforeground="#000000",
            relief="flat",
            cursor="hand2",
            command=self.send_message,
            width=9
        )

        self.send_button.grid(
            row=0,
            column=1,
            padx=(0, 12),
            pady=12,
            sticky="ns"
        )

        # ==========================================
        # PROJECT AGENT APPROVAL CONTROLS
        # ==========================================
        self.plan_controls = tk.Frame(
            input_outer,
            bg=self.bg
        )

        self.plan_controls.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(8, 0)
        )

        self.plan_status_label = tk.Label(
            self.plan_controls,
            text="Plan: NONE",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg,
            fg="#888888"
        )

        self.plan_status_label.pack(
            side="left",
            padx=(0, 12)
        )

        self.approve_plan_button = tk.Button(
            self.plan_controls,
            text="Approve Plan",
            font=("Segoe UI", 9, "bold"),
            bg="#1E1E1E",
            fg="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            disabledforeground="#666666",
            relief="flat",
            cursor="hand2",
            command=lambda: self.send_plan_command(
                "setujui plan"
            ),
            state="disabled"
        )

        self.approve_plan_button.pack(
            side="left",
            padx=(0, 6)
        )

        self.cancel_plan_button = tk.Button(
            self.plan_controls,
            text="Cancel Plan",
            font=("Segoe UI", 9, "bold"),
            bg="#1E1E1E",
            fg="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            disabledforeground="#666666",
            relief="flat",
            cursor="hand2",
            command=lambda: self.send_plan_command(
                "batalkan plan"
            ),
            state="disabled"
        )

        self.cancel_plan_button.pack(
            side="left",
            padx=6
        )

        self.execute_plan_button = tk.Button(
            self.plan_controls,
            text="Execute Plan",
            font=("Segoe UI", 9, "bold"),
            bg="#1E1E1E",
            fg="#FFFFFF",
            activebackground="#303030",
            activeforeground="#FFFFFF",
            disabledforeground="#666666",
            relief="flat",
            cursor="hand2",
            command=lambda: self.send_plan_command(
                "jalankan plan"
            ),
            state="disabled"
        )

        self.execute_plan_button.pack(
            side="left",
            padx=6
        )

        self.refresh_plan_controls()

        self.entry.focus_set()

        # ==========================================
        # STARTUP
        # ==========================================
        self.startup_chat()

        # STREAMING RESPONSE CHECK
        self.root.after(
            50,
            self.check_response_queue
        )

        # OLLAMA STATUS CHECK
        self.root.after(
            100,
            self.check_status_queue
        )

        self.root.after(
            200,
            self.request_status_check
        )

    # ==========================================
    # SIDEBAR BUTTON HELPER
    # ==========================================
    def make_sidebar_button(
        self,
        text,
        command=None,
        bold=False
    ):

        button = tk.Button(
            self.sidebar,
            text=text,
            anchor="w",
            font=(
                "Segoe UI",
                10,
                "bold" if bold else "normal"
            ),
            bg=(
                self.button_bg
                if bold
                else self.sidebar_bg
            ),
            fg=(
                self.text_color
                if bold
                else self.secondary_text
            ),
            activebackground=self.active_bg,
            activeforeground=self.text_color,
            relief="flat",
            cursor="hand2",
            command=command
        )

        button.pack(
            fill="x",
            padx=15,
            pady=4,
            ipady=8
        )

        return button

    # ==========================================
    # OLLAMA STATUS REQUEST
    # ==========================================
    def request_status_check(self):

        if not self.status_check_running:

            self.status_check_running = True

            worker = threading.Thread(
                target=self.status_worker,
                daemon=True
            )

            worker.start()

        # Cek lagi setiap 5 detik
        self.root.after(
            5000,
            self.request_status_check
        )

    # ==========================================
    # OLLAMA STATUS WORKER
    # ==========================================
    def status_worker(self):

        try:

            status = check_ollama_status()

        except Exception:

            status = {
                "online": False,
                "model_available": False,
                "model": "qwen3:8b"
            }

        self.status_queue.put(
            status
        )

    # ==========================================
    # STATUS QUEUE
    # ==========================================
    def check_status_queue(self):

        try:

            while True:

                status = (
                    self.status_queue.get_nowait()
                )

                self.update_status_display(
                    status
                )

                self.status_check_running = False

        except queue.Empty:

            pass

        self.root.after(
            100,
            self.check_status_queue
        )

    # ==========================================
    # UPDATE STATUS DISPLAY
    # ==========================================
    def update_status_display(
        self,
        status
    ):

        online = status.get(
            "online",
            False
        )

        model_available = status.get(
            "model_available",
            False
        )

        model = status.get(
            "model",
            "qwen3:8b"
        )

        # Ollama + model tersedia
        if online and model_available:

            header_text = (
                f"● ONLINE — {model}"
            )

            sidebar_text = (
                f"●  {model}"
            )

            color = self.online_color

        # Ollama hidup tetapi model hilang
        elif online:

            header_text = (
                "● MODEL NOT FOUND"
            )

            sidebar_text = (
                "●  MODEL MISSING"
            )

            color = self.warning_color

        # Ollama mati
        else:

            header_text = (
                "● OFFLINE"
            )

            sidebar_text = (
                "●  OLLAMA OFFLINE"
            )

            color = self.offline_color

        self.header_status.configure(
            text=header_text,
            fg=color
        )

        self.sidebar_status.configure(
            text=sidebar_text,
            fg=color
        )

    # ==========================================
    # INLINE MARKDOWN
    # ==========================================
    def insert_inline_markdown(
        self,
        text
    ):

        pattern = re.compile(
            r"(\*\*.*?\*\*|`.*?`)"
        )

        position = 0

        for match in pattern.finditer(
            text
        ):

            before = text[
                position:match.start()
            ]

            if before:

                self.chat.insert(
                    tk.END,
                    before,
                    "message"
                )

            token = match.group(0)

            if token.startswith("**"):

                self.chat.insert(
                    tk.END,
                    token[2:-2],
                    "bold"
                )

            elif token.startswith("`"):

                self.chat.insert(
                    tk.END,
                    token[1:-1],
                    "code"
                )

            position = match.end()

        remaining = text[position:]

        if remaining:

            self.chat.insert(
                tk.END,
                remaining,
                "message"
            )

    # ==========================================
    # MARKDOWN RENDERER
    # ==========================================
    def insert_markdown(
        self,
        text
    ):

        lines = text.splitlines(
            keepends=True
        )

        if not lines and text:
            lines = [text]

        for line in lines:

            has_newline = line.endswith(
                "\n"
            )

            clean_line = line.rstrip(
                "\n"
            )

            stripped = clean_line.lstrip()

            # H1
            if stripped.startswith("# "):

                content = stripped[2:]

                content = re.sub(
                    r"\*\*(.*?)\*\*",
                    r"\1",
                    content
                )

                self.chat.insert(
                    tk.END,
                    content,
                    "heading1"
                )

            # H2
            elif stripped.startswith("## "):

                content = stripped[3:]

                content = re.sub(
                    r"\*\*(.*?)\*\*",
                    r"\1",
                    content
                )

                self.chat.insert(
                    tk.END,
                    content,
                    "heading2"
                )

            # H3
            elif stripped.startswith("### "):

                content = stripped[4:]

                content = re.sub(
                    r"\*\*(.*?)\*\*",
                    r"\1",
                    content
                )

                self.chat.insert(
                    tk.END,
                    content,
                    "heading3"
                )

            # BULLET
            elif (
                stripped.startswith("- ")
                or stripped.startswith("* ")
            ):

                content = stripped[2:]

                self.chat.insert(
                    tk.END,
                    "• ",
                    "bullet"
                )

                self.insert_inline_markdown(
                    content
                )

            # QUOTE
            elif stripped.startswith("> "):

                content = stripped[2:]

                self.chat.insert(
                    tk.END,
                    "│ " + content,
                    "quote"
                )

            # SEPARATOR
            elif stripped in [
                "---",
                "***"
            ]:

                self.chat.insert(
                    tk.END,
                    "────────────────────────",
                    "system"
                )

            # NUMBERED LIST
            elif re.match(
                r"^\d+\.\s+",
                stripped
            ):

                match = re.match(
                    r"^(\d+\.)\s+(.*)",
                    stripped
                )

                if match:

                    number = match.group(1)
                    content = match.group(2)

                    self.chat.insert(
                        tk.END,
                        number + " ",
                        "bold"
                    )

                    self.insert_inline_markdown(
                        content
                    )

            # NORMAL TEXT
            else:

                self.insert_inline_markdown(
                    clean_line
                )

            if has_newline:

                self.chat.insert(
                    tk.END,
                    "\n",
                    "message"
                )

    # ==========================================
    # STARTUP CHAT
    # ==========================================
    def startup_chat(self):

        chats = get_all_chats()

        if chats:

            self.current_chat_id = (
                chats[0]["id"]
            )

            self.load_chat(
                self.current_chat_id
            )

        else:

            self.create_new_chat()

        self.refresh_history()

    # ==========================================
    # CREATE NEW CHAT
    # ==========================================
    def create_new_chat(self):

        self.current_chat_id = create_chat(
            "New Chat"
        )

        self.clear_chat()

        self.show_welcome()

        self.header_title.configure(
            text="New Chat"
        )

        self.refresh_history()

    # ==========================================
    # NEW CHAT
    # ==========================================
    def new_chat(self):

        if self.is_generating:
            return

        self.create_new_chat()

        self.entry.focus_set()

    # ==========================================
    # CLEAR CHAT
    # ==========================================
    def clear_chat(self):

        self.chat.configure(
            state="normal"
        )

        self.chat.delete(
            "1.0",
            tk.END
        )

        self.chat.configure(
            state="disabled"
        )

    # ==========================================
    # WELCOME
    # ==========================================
    def show_welcome(self):

        self.chat.configure(
            state="normal"
        )

        self.chat.insert(
            tk.END,
            "SHIVA ORIGIN v0.1 by Yuwwa\n",
            "system"
        )

        self.chat.insert(
            tk.END,
            "Personal AI Operating System\n\n",
            "system"
        )

        self.chat.insert(
            tk.END,
            "SHIVA: ",
            "name"
        )

        self.chat.insert(
            tk.END,
            "Halo. Saya SHIVA. Apa yang ingin kamu kerjakan?\n\n",
            "message"
        )

        self.chat.configure(
            state="disabled"
        )

    # ==========================================
    # APPEND CHAT
    # ==========================================
    def append_chat(
        self,
        speaker,
        message
    ):

        self.chat.configure(
            state="normal"
        )

        self.chat.insert(
            tk.END,
            f"{speaker}: ",
            "name"
        )

        self.chat.insert(
            tk.END,
            f"{message}\n\n",
            "message"
        )

        self.chat.configure(
            state="disabled"
        )

        self.chat.see(
            tk.END
        )

    # ==========================================
    # HISTORY SIDEBAR
    # ==========================================
    def refresh_history(self):

        for widget in (
            self.history_frame.winfo_children()
        ):

            widget.destroy()

        chats = get_all_chats()

        for chat_data in chats[:10]:

            title = chat_data.get(
                "title",
                "New Chat"
            )

            if len(title) > 25:

                title = (
                    title[:25]
                    + "..."
                )

            is_active = (
                chat_data["id"]
                == self.current_chat_id
            )

            row = tk.Frame(
                self.history_frame,
                bg=self.sidebar_bg
            )

            row.pack(
                fill="x",
                pady=2
            )

            button = tk.Button(
                row,
                text=title,
                anchor="w",
                font=("Segoe UI", 9),
                bg=(
                    self.active_bg
                    if is_active
                    else self.sidebar_bg
                ),
                fg=(
                    self.text_color
                    if is_active
                    else self.secondary_text
                ),
                activebackground=self.active_bg,
                activeforeground=self.text_color,
                relief="flat",
                cursor="hand2",
                command=lambda chat_id=chat_data["id"]:
                    self.open_chat(chat_id)
            )

            button.pack(
                side="left",
                fill="x",
                expand=True,
                ipady=5
            )

            delete_button = tk.Button(
                row,
                text="Delete",
                font=("Segoe UI", 9, "bold"),
                bg=self.sidebar_bg,
                fg=self.secondary_text,
                activebackground=self.active_bg,
                activeforeground=self.text_color,
                relief="flat",
                cursor="hand2",
                width=3,
                command=lambda chat_id=chat_data["id"]:
                    self.delete_history_chat(chat_id)
            )

            delete_button.pack(
                side="right",
                padx=(4, 0),
                ipady=4
            )

    # ==========================================
    # DELETE HISTORY CHAT
    # ==========================================
    def delete_history_chat(
        self,
        chat_id
    ):
        if self.is_generating:
            return

        deleted = delete_chat(
            chat_id
        )

        if not deleted:
            return

        if self.current_chat_id == chat_id:
            self.create_new_chat()
        else:
            self.refresh_history()

    # ==========================================
    # OPEN CHAT
    # ==========================================
    def open_chat(
        self,
        chat_id
    ):

        if self.is_generating:
            return

        self.current_chat_id = chat_id

        self.load_chat(
            chat_id
        )

        self.refresh_history()

        self.entry.focus_set()

    # ==========================================
    # LOAD CHAT
    # ==========================================
    def load_chat(
        self,
        chat_id
    ):

        chat_data = get_chat(
            chat_id
        )

        if not chat_data:
            return

        self.clear_chat()

        title = chat_data.get(
            "title",
            "New Chat"
        )

        self.header_title.configure(
            text=title
        )

        messages = chat_data.get(
            "messages",
            []
        )

        if not messages:

            self.show_welcome()
            return

        self.chat.configure(
            state="normal"
        )

        self.chat.insert(
            tk.END,
            "SHIVA ORIGIN v0.1 by Yuwwa\n\n",
            "system"
        )

        for message in messages:

            role = message.get(
                "role",
                ""
            )

            content = message.get(
                "content",
                ""
            )

            if role == "user":

                self.chat.insert(
                    tk.END,
                    "YOU: ",
                    "name"
                )

                self.chat.insert(
                    tk.END,
                    content + "\n\n",
                    "message"
                )

            else:

                self.chat.insert(
                    tk.END,
                    "SHIVA: ",
                    "name"
                )

                self.insert_markdown(
                    content
                )

                self.chat.insert(
                    tk.END,
                    "\n\n",
                    "message"
                )

        self.chat.configure(
            state="disabled"
        )

        self.chat.see(
            tk.END
        )

    # ==========================================
    # MEMORY
    # ==========================================
    def show_memory_info(self):

        memory_window = tk.Toplevel(self.root)
        MemoryCenter(memory_window)

    # ==========================================
    # CAPABILITIES
    # ==========================================
    def show_capabilities(self):

        capabilities_window = tk.Toplevel(self.root)
        CapabilitiesCenter(capabilities_window)

    # ==========================================
    # PROJECT WORKSPACE
    # ==========================================
    def show_projects(self):

        project_window = tk.Toplevel(
            self.root
        )

        ProjectCenter(
            project_window
        )

    # ==========================================
    # OPEN LIVE PREVIEW
    # ==========================================
    # ==========================================
    # SHIVA SECURITY
    # ==========================================
    def show_security(self):

        runtime_result = (
            self.security_runtime.build_application_result()
        )

        application_result = runtime_result.get(
            "application"
        )

        security_window = tk.Toplevel(self.root)

        ShivaSecurityWindow(
            security_window,
            application_result=application_result
        )

    def open_live_preview(self):

        result = (
            self.preview_controller.open_preview()
        )

        if result.get(
            "ok",
            False
        ):

            status = result.get(
                "status",
                ""
            )

            if status == "already_running":

                self.preview_status.configure(
                    text="OPEN"
                )

            else:

                self.preview_status.configure(
                    text="RUNNING"
                )

        else:

            self.preview_status.configure(
                text="ERROR"
            )

    # ==========================================
    # REFRESH LIVE PREVIEW
    # ==========================================
    def refresh_live_preview(self):

        self.preview_status.configure(
            text="REFRESHING"
        )

        result = (
            self.preview_controller.refresh_preview()
        )

        if result.get(
            "ok",
            False
        ):

            self.preview_status.configure(
                text="RUNNING"
            )

        else:

            self.preview_status.configure(
                text="ERROR"
            )

    # ==========================================
    # CLOSE LIVE PREVIEW
    # ==========================================
    def close_live_preview(self):

        result = (
            self.preview_controller.close_preview()
        )

        if result.get(
            "ok",
            False
        ):

            self.preview_status.configure(
                text="CLOSED"
            )

        else:

            self.preview_status.configure(
                text="ERROR"
            )

    # ==========================================
    # PLAN CONTROL STATES
    # ==========================================
    def set_plan_control_states(
        self,
        approve=False,
        cancel=False,
        execute=False
    ):

        if not hasattr(
            self,
            "approve_plan_button"
        ):
            return

        self.approve_plan_button.configure(
            state=(
                "normal"
                if approve
                else "disabled"
            )
        )

        self.cancel_plan_button.configure(
            state=(
                "normal"
                if cancel
                else "disabled"
            )
        )

        self.execute_plan_button.configure(
            state=(
                "normal"
                if execute
                else "disabled"
            )
        )

    # ==========================================
    # REFRESH PLAN CONTROLS
    # ==========================================
    def refresh_plan_controls(self):

        if not hasattr(
            self,
            "plan_status_label"
        ):
            return

        try:

            plan_lock = ProjectPlanLock()

            result = (
                plan_lock.verify_lock()
            )

        except Exception:

            result = {
                "ok": False
            }

        if not result.get(
            "ok",
            False
        ):

            self.plan_status_label.configure(
                text="Plan: NONE"
            )

            self.set_plan_control_states(
                False,
                False,
                False
            )

            return

        status = str(
            result.get(
                "status",
                "unknown"
            )
        ).lower()

        self.plan_status_label.configure(
            text=f"Plan: {status.upper()}"
        )

        if status == "pending":

            self.set_plan_control_states(
                approve=True,
                cancel=True,
                execute=False
            )

        elif status == "approved":

            self.set_plan_control_states(
                approve=False,
                cancel=True,
                execute=True
            )

        else:

            self.set_plan_control_states(
                approve=False,
                cancel=False,
                execute=False
            )

    # ==========================================
    # SEND PLAN COMMAND THROUGH CHAT PIPELINE
    # ==========================================
    def send_plan_command(
        self,
        command
    ):

        if self.is_generating:
            return

        self.entry.configure(
            state="normal"
        )

        self.entry.delete(
            0,
            tk.END
        )

        self.entry.insert(
            0,
            command
        )

        self.send_message()

    # ==========================================
    # SEND MESSAGE
    # ==========================================
    def send_message(
        self,
        event=None
    ):

        if self.is_generating:
            return

        user_input = (
            self.entry.get().strip()
        )

        if not user_input:
            return

        if not self.current_chat_id:
            self.create_new_chat()

        self.entry.delete(
            0,
            tk.END
        )

        self.append_chat(
            "YOU",
            user_input
        )

        add_message(
            self.current_chat_id,
            "user",
            user_input
        )

        chat_data = get_chat(
            self.current_chat_id
        )

        if (
            chat_data
            and chat_data.get("title")
            == "New Chat"
        ):

            new_title = (
                user_input.strip()
            )

            if len(new_title) > 35:

                new_title = (
                    new_title[:35]
                    + "..."
                )

            rename_chat(
                self.current_chat_id,
                new_title
            )

            self.header_title.configure(
                text=new_title
            )

            self.refresh_history()

        self.is_generating = True
        self.streaming_answer = ""

        self.set_plan_control_states(
            False,
            False,
            False
        )

        self.entry.configure(
            state="disabled"
        )

        self.send_button.configure(
            state="disabled",
            text="..."
        )

        worker = threading.Thread(
            target=self.process_message,
            args=(user_input,),
            daemon=True
        )

        worker.start()

    # ==========================================
    # STREAM PROCESS
    # ==========================================
    def process_message(
        self,
        user_input
    ):

        try:

            self.response_queue.put(
                ("start", None)
            )

            self.response_queue.put(
                ("processing_state", "THINKING")
            )

            self.response_queue.put(
                ("processing_state", "ANALYZING")
            )

            discovered = False

            for chunk in (
                self.brain.process_stream(
                    user_input
                )
            ):

                if not discovered:
                    discovered = True
                    self.response_queue.put(
                        ("processing_state", "DISCOVERED")
                    )

                if (
                    isinstance(chunk, dict)
                    and chunk.get("event") == "security_operation"
                ):
                    self.response_queue.put(
                        (
                            "security_operation",
                            chunk.get("request", {})
                        )
                    )
                else:
                    self.response_queue.put(
                        ("chunk", chunk)
                    )

            self.response_queue.put(
                ("done", None)
            )

        except Exception as error:

            self.response_queue.put(
                (
                    "chunk",
                    f"Terjadi error: {error}"
                )
            )

            self.response_queue.put(
                ("done", None)
            )

    # ==========================================
    # RENDER STREAM
    # ==========================================
    def _chat_is_at_bottom(self):
        try:
            _first, last = self.chat.yview()
            return last >= 0.995
        except tk.TclError:
            return True

    def schedule_stream_render(self):
        if self.stream_render_pending:
            return

        self.stream_render_pending = True
        self.stream_render_after_id = self.root.after(
            100,
            self.flush_stream_render
        )

    def flush_stream_render(self):
        self.stream_render_pending = False
        self.stream_render_after_id = None

        if self.is_generating and self.streaming_answer:
            self.render_streaming_answer()

    def render_streaming_answer(
        self
    ):

        was_at_bottom = self._chat_is_at_bottom()

        try:
            old_top = self.chat.yview()[0]
        except tk.TclError:
            old_top = 1.0

        self.chat.configure(
            state="normal"
        )

        try:

            self.chat.delete(
                "stream_start",
                "end-1c"
            )

        except tk.TclError:

            pass

        self.insert_markdown(
            self.streaming_answer
        )

        self.chat.configure(
            state="disabled"
        )

        if was_at_bottom:

            self.chat.see(
                tk.END
            )

        else:

            try:
                self.chat.yview_moveto(
                    old_top
                )
            except tk.TclError:
                pass

    # ==========================================
    # STREAM QUEUE
    # ==========================================
    def open_security_operation(
        self,
        request
    ):

        if not isinstance(request, dict):
            return

        runtime_result = (
            self.security_runtime.build_application_result()
        )

        application_result = runtime_result.get(
            "application"
        )

        security_window = tk.Toplevel(
            self.root
        )

        security_controller = ShivaSecurityWindow(
            security_window,
            application_result=application_result,
            operation_request=request
        )

        security_controller.open_operation_console()


    def check_response_queue(
        self
    ):

        try:

            while True:

                event_type, data = (
                    self.response_queue.get_nowait()
                )

                if event_type == "start":

                    self.streaming_answer = ""

                    self.chat.configure(
                        state="normal"
                    )

                    self.chat.insert(
                        tk.END,
                        "SHIVA: ",
                        "name"
                    )

                    self.chat.mark_set(
                        "stream_start",
                        "end-1c"
                    )

                    self.chat.mark_gravity(
                        "stream_start",
                        tk.LEFT
                    )

                    self.chat.configure(
                        state="disabled"
                    )

                    self.chat.see(
                        tk.END
                    )

                elif event_type == "processing_state":

                    self.processing_state = data
                elif event_type == "chunk":

                    self.streaming_answer += data

                    self.schedule_stream_render()

                elif event_type == "security_operation":

                    request = (
                        data
                        if isinstance(data, dict)
                        else {}
                    )

                    self.open_security_operation(
                        request
                    )

                elif event_type == "done":

                    if self.stream_render_after_id is not None:

                        try:
                            self.root.after_cancel(
                                self.stream_render_after_id
                            )
                        except (tk.TclError, ValueError):
                            pass

                        self.stream_render_after_id = None

                    self.stream_render_pending = False

                    self.render_streaming_answer()

                    self.chat.configure(
                        state="normal"
                    )

                    self.chat.insert(
                        tk.END,
                        "\n\n",
                        "message"
                    )

                    self.chat.configure(
                        state="disabled"
                    )

                    if self.streaming_answer.strip():

                        add_message(
                            self.current_chat_id,
                            "assistant",
                            self.streaming_answer.strip()
                        )

                    self.streaming_answer = ""

                    self.is_generating = False

                    self.entry.configure(
                        state="normal"
                    )

                    self.send_button.configure(
                        state="normal",
                        text="Send"
                    )

                    self.entry.focus_set()

                    self.refresh_history()

                    self.refresh_plan_controls()

        except queue.Empty:

            pass

        self.root.after(
            50,
            self.check_response_queue
        )


# ==========================================
# START SHIVA
# ==========================================
if __name__ == "__main__":

    root = tk.Tk()

    app = ShivaInterface(root)

    root.mainloop()












