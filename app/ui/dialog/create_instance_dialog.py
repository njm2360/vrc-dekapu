import tkinter as tk
from tkinter import ttk


INSTANCE_NAME_LIST = [
    "リンゴ",
    "イチゴ",
    "メロン",
    "スイカ",
    "バナナ",
    "ブドウ",
    "マンゴー",
    "レモン",
]


class CreateInstanceDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("新規インスタンス作成")
        self.resizable(False, False)
        self.attributes("-toolwindow", True)
        self.result = None

        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="名前:").grid(row=0, column=0, pady=(10, 5), padx=10)

        self.combo = ttk.Combobox(self, values=INSTANCE_NAME_LIST, state="readonly")
        self.combo.current(0)
        self.combo.grid(row=1, column=0, padx=10, sticky="ew")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, pady=10)

        ttk.Button(btn_frame, text="OK", command=self._ok).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).grid(
            row=0, column=1, padx=5
        )

    def _ok(self):
        self.result = self.combo.get()
        self.destroy()
