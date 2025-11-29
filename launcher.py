import tkinter as tk
from app.ui.instance_viewer_app import InstanceViewerApp

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("500x250")
    root.resizable(False, False)
    InstanceViewerApp(root)
    root.mainloop()
