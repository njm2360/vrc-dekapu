import tkinter as tk
from app.ui.instance_viewer_app import InstanceViewerApp
from app.util.logger import setup_logger

setup_logger()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("420x250")
    root.resizable(False, False)
    InstanceViewerApp(root)
    root.mainloop()
