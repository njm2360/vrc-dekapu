import tkinter as tk
from tkinter import ttk


class OSCView(ttk.Frame):
    def __init__(self, parent, on_lock, on_release):
        super().__init__(parent)

        ttk.Label(self, text="OSC IP:").pack(side=tk.LEFT, padx=(5, 5))
        self.ip_entry = ttk.Entry(self, width=12)
        self.ip_entry.pack(side=tk.LEFT)

        ttk.Label(self, text="Port:").pack(side=tk.LEFT, padx=(10, 5))
        self.port_entry = ttk.Entry(self, width=6)
        self.port_entry.pack(side=tk.LEFT)

        btn_release = ttk.Button(self, text="開放", command=on_release)
        btn_release.pack(side=tk.RIGHT, padx=5)

        btn_lock = ttk.Button(self, text="ロック", command=on_lock)
        btn_lock.pack(side=tk.RIGHT, padx=5)
