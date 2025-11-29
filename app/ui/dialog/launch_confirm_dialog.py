import tkinter as tk
from tkinter import ttk


class LaunchConfirmDialog(tk.Toplevel):
    def __init__(self, parent, instance_name: str, profile: int):
        super().__init__(parent)
        self.title("確認")
        self.resizable(False, False)
        self.attributes("-toolwindow", True)

        self.result = None  # "launch" / "copy" / None

        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="以下のインスタンスで起動しますか？").grid(
            row=0, column=0, pady=(10, 5), padx=10
        )
        ttk.Label(self, text=f"インスタンス名：{instance_name}").grid(
            row=1, column=0, pady=5, padx=10
        )
        ttk.Label(self, text=f"プロファイル番号：{profile}").grid(
            row=2, column=0, pady=5, padx=10
        )

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, pady=15)

        ttk.Button(btn_frame, text="はい", command=self._launch).grid(
            row=0, column=0, padx=10
        )
        ttk.Button(btn_frame, text="いいえ", command=self._cancel).grid(
            row=0, column=1, padx=10
        )
        ttk.Button(btn_frame, text="リンクをコピー", command=self._copy).grid(
            row=0, column=2, padx=10
        )

    def _launch(self):
        self.result = "launch"
        self.destroy()

    def _copy(self):
        self.result = "copy"
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()
