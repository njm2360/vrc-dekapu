import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from typing import Callable, Optional
from dataclasses import dataclass

from app.const.group import INSTANCE_NAME_LIST
from app.model.vrchat import GroupRole


@dataclass(frozen=True)
class CreateInstanceInput:
    display_name: Optional[str]
    role_ids: Optional[list[str]]
    queue_enabled: bool


class CreateInstanceDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        group_id: str,
        get_group_roles_fn: Callable[[str], list[GroupRole]],
    ):
        super().__init__(parent)
        self.title("新規インスタンス作成")
        self.resizable(False, False)
        self.attributes("-toolwindow", True)

        self.result: Optional[CreateInstanceInput] = None
        self.columnconfigure(0, weight=1)

        self._group_id = group_id
        self._get_group_roles_fn = get_group_roles_fn
        self._roles_cache: Optional[list[GroupRole]] = None

        # 表示名
        ttk.Label(self, text="表示名").grid(
            row=0, column=0, padx=10, pady=(10, 2), sticky="w"
        )

        self.name_mode = tk.StringVar(value="none")

        name_radio = ttk.Frame(self)
        name_radio.grid(row=1, column=0, padx=10, sticky="w")

        ttk.Radiobutton(
            name_radio,
            text="指定しない",
            value="none",
            variable=self.name_mode,
            command=self._update_name_state,
        ).grid(row=0, column=0, padx=(0, 10))

        ttk.Radiobutton(
            name_radio,
            text="選択",
            value="list",
            variable=self.name_mode,
            command=self._update_name_state,
        ).grid(row=0, column=1, padx=(0, 10))

        ttk.Radiobutton(
            name_radio,
            text="手動",
            value="input",
            variable=self.name_mode,
            command=self._update_name_state,
        ).grid(row=0, column=2)

        self.name_combo = ttk.Combobox(
            self, values=INSTANCE_NAME_LIST, state="disabled"
        )
        self.name_combo.current(0)
        self.name_combo.grid(row=2, column=0, padx=10, sticky="ew")

        self.name_entry = ttk.Entry(self, state="disabled")
        self.name_entry.grid(row=3, column=0, padx=10, sticky="ew")

        # 待機列設定
        self.queue_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="待機列", variable=self.queue_var).grid(
            row=4, column=0, padx=10, pady=(8, 0), sticky="w"
        )

        # ロール設定
        role_frame = ttk.LabelFrame(self, text="ロール")
        role_frame.grid(row=5, column=0, padx=10, pady=(10, 0), sticky="ew")

        self.role_listbox = tk.Listbox(role_frame, height=5)
        self.role_listbox.grid(row=0, column=0, columnspan=2, sticky="ew")

        ttk.Button(role_frame, text="追加", command=self._add_role).grid(
            row=1, column=0, pady=5, sticky="ew"
        )
        ttk.Button(role_frame, text="削除", command=self._remove_role).grid(
            row=1, column=1, pady=5, sticky="ew"
        )

        self._assigned_role_ids: list[str] = []

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=6, column=0, pady=12)

        ttk.Button(btn_frame, text="OK", command=self._ok).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=self.destroy).grid(
            row=0, column=1, padx=5
        )

        self._update_name_state()

    def _load_roles(self) -> list[GroupRole]:
        if self._roles_cache is None:
            self._roles_cache = self._get_group_roles_fn(self._group_id)
        return self._roles_cache

    def _add_role(self):
        roles = self._load_roles()

        available_roles = [r for r in roles if r.id not in self._assigned_role_ids]
        if not available_roles:
            messagebox.showinfo(
                "エラー",
                "追加できるロールがありません。",
                parent=self,
            )
            return

        dlg = tk.Toplevel(self)
        dlg.title("ロール選択")
        dlg.resizable(False, False)
        dlg.attributes("-toolwindow", True)

        lb = tk.Listbox(dlg)
        lb.pack(padx=10, pady=10)

        for r in available_roles:
            lb.insert(tk.END, r.name)

        def select():
            idx = lb.curselection()
            if not idx:
                return
            role: GroupRole = available_roles[idx[0]]
            self._assigned_role_ids.append(role.id)
            self.role_listbox.insert(tk.END, role.name)
            dlg.destroy()

        ttk.Button(dlg, text="OK", command=select).pack(pady=(0, 10))

    def _remove_role(self):
        idx = self.role_listbox.curselection()
        if not idx:
            return

        index = idx[0]
        self.role_listbox.delete(index)
        del self._assigned_role_ids[index]

    def _update_name_state(self):
        mode = self.name_mode.get()

        if mode == "list":
            self.name_combo.configure(state="readonly")
            self.name_entry.configure(state="disabled")
        elif mode == "input":
            self.name_combo.configure(state="disabled")
            self.name_entry.configure(state="normal")
        else:  # none
            self.name_combo.configure(state="disabled")
            self.name_entry.configure(state="disabled")

    def _ok(self):
        mode = self.name_mode.get()

        if mode == "none":
            display_name = None
        elif mode == "list":
            display_name = self.name_combo.get()
        else:  # input
            value = self.name_entry.get().strip()
            if not value:
                messagebox.showerror(
                    "エラー",
                    "表示名を入力してください。",
                    parent=self,
                )
                return
            display_name = value

        self.result = CreateInstanceInput(
            display_name=display_name,
            role_ids=self._assigned_role_ids.copy(),
            queue_enabled=self.queue_var.get(),
        )

        self.destroy()
