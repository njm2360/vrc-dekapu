from datetime import datetime
import logging
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox
from app.controller.instance_controller import InstanceController
from app.controller.osc_controller import OSCController
from app.model.vrchat import InstanceInfo
from app.ui.header_view import HeaderView
from app.ui.osc_view import OSCView
from app.ui.instance_table_view import InstanceTableView
from app.ui.dialog.create_instance_dialog import CreateInstanceDialog
from app.ui.dialog.launch_confirm_dialog import LaunchConfirmDialog


class InstanceViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ブッパ連合管理ツール")

        f = tkFont.nametofont("TkDefaultFont")
        f.configure(family="Yu Gothic UI", size=10)

        try:
            self.inst_ctrl = InstanceController()
            self.osc_ctrl = OSCController()
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            root.destroy()
            return

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()
        self.update_instances()

    def on_close(self):
        try:
            self.inst_ctrl.save_session()
        except Exception as e:
            logging.error(e)
        self.root.destroy()

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        main.rowconfigure(0, weight=0)  # Header
        main.rowconfigure(1, weight=0)  # OSC
        main.rowconfigure(2, weight=1)  # Table + label
        main.columnconfigure(0, weight=1)

        # --- Header ---
        self.header = HeaderView(
            main,
            on_update=self.update_instances,
            on_launch=self.launch_selected,
            on_create=self.open_create_dialog,
            on_close=self.close_selected,
        )
        self.header.grid(row=0, column=0, sticky="ew")

        self.header.profile_entry.insert(0, str(self.inst_ctrl.get_profile()))
        self.header.args_entry.insert(
            0, "--process-priority=2 --main-thread-priority=2"
        )

        # --- OSC ---
        self.osc = OSCView(
            main, on_lock=self.send_osc_lock, on_release=self.send_osc_release
        )
        self.osc.grid(row=1, column=0, sticky="ew", pady=5)

        self.osc.ip_entry.insert(0, "127.0.0.1")
        self.osc.port_entry.insert(0, "9000")

        # --- Table ---
        self.table = InstanceTableView(main)
        self.table.grid(row=2, column=0, sticky="nsew")

        main.rowconfigure(2, weight=1)
        main.columnconfigure(0, weight=1)

        # --- Refresh Time ---
        self.last_updated_label = ttk.Label(main, text="更新日時: -")
        self.last_updated_label.grid(row=3, column=0, sticky="w", pady=(5, 0))

    def update_instances(self):
        self.table.delete(*self.table.get_children())
        try:
            instances = self.inst_ctrl.update_instances()
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return

        for inst in instances:
            self.table.insert(
                "",
                tk.END,
                values=(
                    inst.display_name or inst.name,
                    inst.user_count,
                    (
                        inst.closed_at.strftime("%Y-%m-%d %H:%M")
                        if inst.closed_at
                        else "-"
                    ),
                ),
            )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_updated_label.config(text=f"更新日時：{now}")

    def get_selected_index(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("警告", "インスタンスを選択してください")
            return None
        return self.table.index(sel[0])

    def launch_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        profile = int(self.header.profile_entry.get())
        args = self.header.args_entry.get().split()
        try:
            self.inst_ctrl.launch_instance_by_index(idx, profile, args)
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def close_selected(self):
        idx = self.get_selected_index()
        if idx is None:
            return
        name = self.inst_ctrl.get_instance_name(idx)

        if not messagebox.askyesno(
            "確認", f"インスタンスをクローズしますか？\n\n名前: {name}"
        ):
            return
        try:
            self.inst_ctrl.close_instance(idx)
            messagebox.showinfo("完了", "インスタンスをクローズしました")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    # -------- Create ----------
    def open_create_dialog(self):
        dlg = CreateInstanceDialog(self.root)
        self.root.wait_window(dlg)

        if dlg.result is None:
            return

        name = dlg.result
        profile = int(self.header.profile_entry.get())
        args = self.header.args_entry.get().split()

        try:
            inst = self.inst_ctrl.create_instance(name)
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return

        self.confirm_instance_launch(inst, profile, args)

    def confirm_instance_launch(self, inst: InstanceInfo, profile: int, args):
        dlg = LaunchConfirmDialog(
            self.root, instance_name=(inst.display_name or inst.name), profile=profile
        )
        self.root.wait_window(dlg)

        if dlg.result == "launch":
            try:
                self.inst_ctrl.launch_instance(inst, profile, args)
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

    # -------- OSC ----------
    def send_osc_lock(self):
        ip = self.osc.ip_entry.get()
        try:
            port = int(self.osc.port_entry.get())
            self.osc_ctrl.lock(ip, port)
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def send_osc_release(self):
        ip = self.osc.ip_entry.get()
        try:
            port = int(self.osc.port_entry.get())
            self.osc_ctrl.release(ip, port)
        except Exception as e:
            messagebox.showerror("エラー", str(e))
