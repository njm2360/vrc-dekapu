from tkinter import ttk
import tkinter as tk


class HeaderView(ttk.Frame):
    def __init__(
        self,
        parent,
        on_update,
        on_launch,
        on_create,
        on_close,
        on_group_change,
        group_names: list[str],
    ):
        super().__init__(parent)

        for c in range(8):
            self.columnconfigure(c, weight=0)
        self.columnconfigure(7, weight=1)

        # 1段目：グループ / プロファイル
        ttk.Label(self, text="グループ:").grid(row=0, column=0, padx=5, pady=2)

        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(
            self,
            textvariable=self.group_var,
            values=group_names,
            state="readonly",
            width=12,
        )
        self.group_combo.grid(row=0, column=1, padx=(0, 10), pady=2)
        self.group_combo.bind("<<ComboboxSelected>>", on_group_change)

        if group_names:
            self.group_combo.current(0)

        ttk.Label(self, text="プロファイル番号:").grid(row=0, column=2, padx=5, pady=2)
        self.profile_entry = ttk.Entry(self, width=5)
        self.profile_entry.grid(row=0, column=3, sticky="w", padx=(0, 5), pady=2)

        # 2段目：ボタン類
        ttk.Button(self, text="更新", command=on_update).grid(
            row=1, column=0, padx=5, pady=2
        )
        ttk.Button(self, text="起動", command=on_launch).grid(
            row=1, column=1, padx=5, pady=2
        )
        ttk.Button(self, text="作成", command=on_create).grid(
            row=1, column=2, padx=5, pady=2
        )
        ttk.Button(self, text="クローズ", command=on_close).grid(
            row=1, column=3, padx=5, pady=2
        )

        # 3段目：起動引数
        ttk.Label(self, text="起動引数:").grid(row=2, column=0, padx=5, pady=(2, 0))
        self.args_entry = ttk.Entry(self)
        self.args_entry.grid(
            row=2, column=1, columnspan=7, sticky="ew", padx=5, pady=(2, 0)
        )
