from tkinter import ttk


class HeaderView(ttk.Frame):
    def __init__(self, parent, on_update, on_launch, on_create, on_close):
        super().__init__(parent)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=0)
        self.columnconfigure(4, weight=0)
        self.columnconfigure(5, weight=1)

        ttk.Button(self, text="更新", command=on_update).grid(
            row=0, column=0, padx=5, pady=2
        )
        ttk.Button(self, text="起動", command=on_launch).grid(
            row=0, column=1, padx=5, pady=2
        )
        ttk.Button(self, text="作成", command=on_create).grid(
            row=0, column=2, padx=5, pady=2
        )
        ttk.Button(self, text="クローズ", command=on_close).grid(
            row=0, column=3, padx=5, pady=2
        )

        ttk.Label(self, text="プロファイル:").grid(row=0, column=4, padx=5)
        self.profile_entry = ttk.Entry(self, width=5)
        self.profile_entry.grid(row=0, column=5, sticky="w", padx=(0, 5))

        ttk.Label(self, text="起動引数:").grid(row=1, column=0, padx=5, pady=(2, 0))
        self.args_entry = ttk.Entry(self)
        self.args_entry.grid(
            row=1, column=1, columnspan=5, sticky="ew", padx=5, pady=(2, 0)
        )
