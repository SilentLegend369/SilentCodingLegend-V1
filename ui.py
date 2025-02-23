import tkinter as tk
from tkinter import ttk
import threading
from typing import Optional, Callable
import logging

class SuggestionWindow:
    def __init__(self):
        self.window: Optional[tk.Tk] = None
        self.suggestion_text: Optional[tk.Text] = None
        self._setup_window()

    def _setup_window(self):
        """Initialize the suggestion window."""
        self.window = tk.Tk()
        self.window.title("Silent Coding Legend - Suggestions")
        self.window.attributes('-topmost', True)
        self.window.withdraw()  # Hide window initially

        # Configure style
        style = ttk.Style()
        style.configure('Suggestion.TFrame', background='#2E3440')
        
        # Main frame
        main_frame = ttk.Frame(self.window, style='Suggestion.TFrame', padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Suggestion text area
        self.suggestion_text = tk.Text(
            main_frame,
            wrap=tk.WORD,
            height=10,
            width=60,
            font=('Consolas', 10),
            bg='#3B4252',
            fg='#ECEFF4',
            insertbackground='#ECEFF4'
        )
        self.suggestion_text.grid(row=0, column=0, padx=5, pady=5)

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.suggestion_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.suggestion_text['yscrollcommand'] = scrollbar.set

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=5)

        # Buttons
        ttk.Button(button_frame, text="Accept (Ctrl+Enter)", command=self.accept).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Dismiss (Esc)", command=self.hide).pack(side=tk.LEFT, padx=5)

        # Configure window behavior
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.bind('<Escape>', lambda e: self.hide())

    def show(self, suggestion: str, x: int, y: int):
        """Show the suggestion window at the specified coordinates."""
        if not self.window:
            self._setup_window()

        self.suggestion_text.delete('1.0', tk.END)
        self.suggestion_text.insert('1.0', suggestion)
        
        # Position window near cursor but not under it
        self.window.geometry(f"+{x+20}+{y+20}")
        self.window.deiconify()
        self.window.lift()
        self.suggestion_text.focus_set()

    def hide(self):
        """Hide the suggestion window."""
        if self.window:
            self.window.withdraw()

    def accept(self):
        """Accept the current suggestion."""
        if self.window and self.suggestion_text:
            suggestion = self.suggestion_text.get('1.0', tk.END).strip()
            self.hide()
            return suggestion
        return None

class StatusBar:
    def __init__(self):
        self.window: Optional[tk.Tk] = None
        self.status_label: Optional[tk.Label] = None
        self._setup_window()

    def _setup_window(self):
        """Initialize the status bar window."""
        self.window = tk.Tk()
        self.window.title("")
        self.window.attributes('-topmost', True, '-alpha', 0.9)
        self.window.overrideredirect(True)  # Remove window decorations

        # Status label
        self.status_label = tk.Label(
            self.window,
            text="Silent Coding Legend: Active",
            font=('Helvetica', 10),
            bg='#2E3440',
            fg='#A3BE8C',
            padx=10,
            pady=5
        )
        self.status_label.pack(fill=tk.X)

        # Position window at bottom right
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        self.window.geometry(f"+{screen_width-300}+{screen_height-80}")

    def update_status(self, status: str, status_type: str = "info"):
        """Update the status bar text and color."""
        if not self.status_label:
            return

        colors = {
            "info": "#A3BE8C",    # Green
            "warning": "#EBCB8B", # Yellow
            "error": "#BF616A"    # Red
        }
        
        self.status_label.config(
            text=f"Silent Coding Legend: {status}",
            fg=colors.get(status_type, colors["info"])
        )

    def show(self):
        """Show the status bar."""
        if self.window:
            self.window.deiconify()

    def hide(self):
        """Hide the status bar."""
        if self.window:
            self.window.withdraw()

class NotificationManager:
    def __init__(self):
        self.notifications: list = []
        self.window: Optional[tk.Tk] = None

    def show_notification(self, message: str, duration: int = 3000):
        """Show a temporary notification."""
        if not self.window:
            self.window = tk.Tk()
            self.window.withdraw()

        notification = tk.Toplevel(self.window)
        notification.attributes('-topmost', True, '-alpha', 0.9)
        notification.overrideredirect(True)

        # Create notification content
        frame = ttk.Frame(notification, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text=message,
            font=('Helvetica', 10)
        ).pack()

        # Position notification
        screen_width = notification.winfo_screenwidth()
        screen_height = notification.winfo_screenheight()
        notification.geometry(f"+{screen_width-300}+{screen_height-120}")

        # Auto-hide after duration
        notification.after(duration, lambda: self._hide_notification(notification))

    def _hide_notification(self, notification: tk.Toplevel):
        """Hide and destroy a notification window."""
        notification.destroy()

class UI:
    def __init__(self):
        self.suggestion_window = SuggestionWindow()
        self.status_bar = StatusBar()
        self.notification_manager = NotificationManager()
        self._setup_ui_thread()

    def _setup_ui_thread(self):
        """Setup a separate thread for UI operations."""
        self.ui_thread = threading.Thread(target=self._run_ui_loop, daemon=True)
        self.ui_thread.start()

    def _run_ui_loop(self):
        """Run the UI event loop."""
        try:
            tk.mainloop()
        except Exception as e:
            logging.error(f"UI loop error: {str(e)}")

    def show_suggestion(self, suggestion: str, x: int, y: int):
        """Show a code suggestion."""
        self.suggestion_window.show(suggestion, x, y)

    def update_status(self, status: str, status_type: str = "info"):
        """Update the status bar."""
        self.status_bar.update_status(status, status_type)

    def show_notification(self, message: str, duration: int = 3000):
        """Show a temporary notification."""
        self.notification_manager.show_notification(message, duration)

    def cleanup(self):
        """Clean up UI resources."""
        if self.suggestion_window.window:
            self.suggestion_window.window.destroy()
        if self.status_bar.window:
            self.status_bar.window.destroy()