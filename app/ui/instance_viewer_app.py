import logging
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox

from app.const.group import GROUPNAME_MAP, TZ
from app.model.vrchat import InstanceInfo
from app.ui.header_view import HeaderView
from app.ui.instance_table_view import InstanceTableView
from app.ui.dialog.create_instance_dialog import CreateInstanceDialog
from app.ui.dialog.launch_confirm_dialog import LaunchConfirmDialog
from app.controller.instance_controller import InstanceController


class InstanceViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("グループインスタンス管理ツール")

        f = tkFont.nametofont("TkDefaultFont")
        f.configure(family="Yu Gothic UI", size=10)

        try:
            self.inst_ctrl = InstanceController()
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            root.destroy()
            return

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()

        group_name = self.header.group_combo.get()
        self.current_group_id = GROUPNAME_MAP[group_name]
        self.update_instances(refresh=True)

    def on_close(self):
        try:
            self.inst_ctrl.save_session()
        except Exception as e:
            logging.error(e)
        self.root.destroy()

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=5)
        main.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        main.rowconfigure(0, weight=0)  # Header
        main.rowconfigure(2, weight=1)  # Table + label
        main.columnconfigure(0, weight=1)

        # --- Header ---
        self.header = HeaderView(
            main,
            on_update=lambda: self.update_instances(refresh=True),
            on_launch=self.launch_selected,
            on_create=self.open_create_dialog,
            on_close=self.close_selected,
            on_group_change=self.on_group_change,
            group_names=list(GROUPNAME_MAP.keys()),
        )

        self.header.grid(row=0, column=0, sticky="ew", pady=5)

        self.header.profile_entry.insert(0, str(self.inst_ctrl.get_profile()))
        self.header.args_entry.insert(
            0, "--process-priority=2 --main-thread-priority=2"
        )

        # --- Table ---
        self.table = InstanceTableView(main)
        self.table.grid(row=2, column=0, sticky="nsew")

        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        # --- Refresh Time ---
        self.last_updated_label = ttk.Label(main, text="更新日時: -")
        self.last_updated_label.grid(row=3, column=0, sticky="w", pady=(5, 0))

    def update_instances(self, refresh: bool = False):
        try:
            cache = self.inst_ctrl.get_group_instances(
                group_id=self.current_group_id,
                refresh=refresh,
            )
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return

        self.table.delete(*self.table.get_children())

        for inst in cache.instances:
            self.table.insert(
                "",
                tk.END,
                iid=inst.id,
                values=(
                    inst.display_name or inst.name,
                    inst.user_count,
                    (
                        inst.closed_at.astimezone(TZ).strftime("%Y-%m-%d %H:%M")
                        if inst.closed_at
                        else "-"
                    ),
                ),
            )

        self.last_updated_label.config(
            text=f"更新日時：{cache.updated_at.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def launch_selected(self):
        group_id = self.current_group_id
        id = self._get_selected_id()
        inst = self.inst_ctrl.get_instance_by_id(group_id, id)

        if inst.closed_at:
            messagebox.showerror("エラー", "すでにクローズされています")
            return

        profile = int(self.header.profile_entry.get())
        args = self.header.args_entry.get().split()

        self.confirm_instance_launch(inst, profile, args)

    def close_selected(self):
        group_id = self.current_group_id
        id = self._get_selected_id()
        inst = self.inst_ctrl.get_instance_by_id(group_id, id)

        if inst.closed_at:
            messagebox.showerror("エラー", "すでにクローズされています")
            return

        name = inst.display_name or inst.name
        if not messagebox.askyesno(
            "確認", f"インスタンスをクローズしますか？\n\n名前: {name}"
        ):
            return

        try:
            self.inst_ctrl.close_instance(inst)
            messagebox.showinfo("完了", "インスタンスをクローズしました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    # -------- Create ----------
    def open_create_dialog(self):
        dlg = CreateInstanceDialog(
            self.root,
            group_id=self.current_group_id,
            get_group_roles_fn=self.inst_ctrl.get_group_roles,
        )
        self.root.wait_window(dlg)

        if dlg.result is None:
            return

        try:
            inst = self.inst_ctrl.create_instance(
                group_id=self.current_group_id, input=dlg.result
            )
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return

        profile = int(self.header.profile_entry.get())
        args = self.header.args_entry.get().split()

        self.confirm_instance_launch(inst, profile, args)

    def confirm_instance_launch(self, inst: InstanceInfo, profile: int, args):
        dlg = LaunchConfirmDialog(
            self.root, instance_name=(inst.display_name or inst.name), profile=profile
        )
        self.root.wait_window(dlg)

        if dlg.result == "launch":
            try:
                self.inst_ctrl.launch(inst, profile, args)
            except Exception as e:
                messagebox.showerror("エラー", str(e))

        elif dlg.result == "copy":
            try:
                url = self.inst_ctrl.get_launch_url(inst)
                self.root.clipboard_clear()
                self.root.clipboard_append(url)
                self.root.update()
                messagebox.showinfo("完了", "リンクをコピーしました。")
            except Exception as e:
                messagebox.showerror("エラー", str(e))

    def on_group_change(self, _):
        group_name = self.header.group_var.get()
        group_id = GROUPNAME_MAP[group_name]

        if self.current_group_id == group_id:
            return

        self.current_group_id = group_id
        self.update_instances(refresh=False)

    def _get_selected_id(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("警告", "インスタンスを選択してください")
            return None
        return sel[0]  # inst.id
