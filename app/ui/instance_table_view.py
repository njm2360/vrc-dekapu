import tkinter as tk
from tkinter import ttk


class InstanceTableView(ttk.Treeview):
    def __init__(self, parent):
        columns = ("name", "count", "closed")
        super().__init__(parent, columns=columns, show="headings", height=1)

        self.heading("name", text="名前")
        self.heading("count", text="人数")
        self.heading("closed", text="クローズ日時")

        self.column("name", width=140, anchor=tk.W)
        self.column("count", width=10, anchor=tk.CENTER)
        self.column("closed", width=80, anchor=tk.CENTER)
