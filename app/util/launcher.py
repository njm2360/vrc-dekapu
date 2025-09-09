import time
import psutil
import logging
import subprocess
import win32gui
import win32con
import win32process
from pathlib import Path
from typing import Final
from typing import Optional
from dataclasses import dataclass

from app.model.vrchat import InstanceInfo


@dataclass
class OscConfig:
    in_port: int
    out_ip: str
    out_port: int


class VRCLauncher:
    LAUNCHER_PATH: Final[Path] = Path(
        r"C:/Program Files (x86)/Steam/steamapps/common/VRChat/launch.exe"
    )
    VRCHAT_PROC_NAME: Final[str] = "VRChat.exe"

    def __init__(self, profile: int, vrchat_path: Path = LAUNCHER_PATH):
        self.vrchat_path = vrchat_path
        self.profile = profile
        self.vrc_pid: Optional[int] = None

        if not self.vrchat_path.exists():
            raise FileNotFoundError(
                f"VRChat executable not found at {self.vrchat_path}"
            )

        matched_pids = []
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            if proc.info["name"] == self.VRCHAT_PROC_NAME:
                cmdline = proc.info.get("cmdline") or []
                if f"--profile={self.profile}" in cmdline:
                    matched_pids.append(proc.info["pid"])

        if len(matched_pids) == 1:
            self.vrc_pid = matched_pids[0]
            logging.info(
                f"Found existing VRChat process for profile No.{self.profile} (PID={self.vrc_pid})"
            )
        elif len(matched_pids) > 1:
            raise RuntimeError(
                f"Multiple VRChat processes found for profile No.{self.profile}: {matched_pids}"
            )

    @property
    def is_running(self) -> bool:
        if self.vrc_pid is None:
            return False
        try:
            proc = psutil.Process(self.vrc_pid)
            return proc.is_running() and proc.name() == self.VRCHAT_PROC_NAME
        except psutil.NoSuchProcess:
            return False

    def launch(
        self,
        instance: Optional[InstanceInfo] = None,
        no_vr: bool = True,
        osc: Optional[OscConfig] = None,
        fps: Optional[int] = None,
        midi: Optional[str] = None,
        startup_timeout: int = 60,
    ):
        args = [str(self.vrchat_path), f"--profile={self.profile}"]

        if instance:
            args.append(self.build_launch_url(instance))
        if osc:
            args.append(f"--osc={osc.in_port}:{osc.out_ip}:{osc.out_port}")
        if midi:
            args.append(f"--midi={midi}")
        if no_vr:
            args.append("--no-vr")
        if fps:
            args.append(f"--fps={fps}")

        try:
            logging.debug(f"Launch args: {args}")
            proc = subprocess.Popen(args)
            logging.debug(f"launch.exe started (PID={proc.pid})")
        except Exception as e:
            logging.error(f"Failed to launch VRChat: {e}")
            return

        # ランチャーの開始時刻以降に起動されたVRChatプロセスを取得する
        launch_time = psutil.Process(proc.pid).create_time()
        self.vrc_pid = self._wait_for_vrchat_process(launch_time, startup_timeout)

        if self.vrc_pid:
            logging.debug(f"VRChat.exe started (PID={self.vrc_pid})")
        else:
            logging.error("Failed to detect VRChat.exe process within timeout")

    def terminate(self, timeout: int = 15) -> bool:
        if not self.vrc_pid:
            return False

        pid = self.vrc_pid
        try:
            hwnd = self._find_window()
            if hwnd:
                # ウィンドウがあればWM_CLOSEでの終了を試みる
                logging.debug(f"Sending WM_CLOSE to hwnd={hwnd} (PID={pid})")
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

                # プロセスの終了を待機、タイムアウト時は強制終了
                try:
                    psutil.Process(pid).wait(timeout=timeout)
                    logging.debug(f"VRChat process (PID={pid}) exited after WM_CLOSE")
                except psutil.TimeoutExpired:
                    logging.warning(
                        f"VRChat process (PID={pid}) did not exit in {timeout}s, forcing terminate"
                    )
                    psutil.Process(pid).kill()
            else:
                # ウィンドウがない場合は強制終了
                logging.warning(
                    f"No visible window found for VRChat (PID={pid}), forcing terminate"
                )
                psutil.Process(pid).kill()

        except Exception as e:
            logging.error(f"Failed to terminate VRChat: {e}")

        alive = psutil.pid_exists(pid)
        if not alive:
            self.vrc_pid = None

        return not alive

    @staticmethod
    def build_launch_url(instance: InstanceInfo) -> str:
        return (
            f"vrchat://launch?ref=VRCQuickLauncher&id={instance.location}"
            f"&shortName={instance.short_name}"
        )

    def _wait_for_vrchat_process(
        self, launch_time: float, timeout: int
    ) -> Optional[int]:
        start = time.time()

        while time.time() - start < timeout:
            for p in psutil.process_iter(attrs=["pid", "name", "create_time"]):
                if p.info["name"] == self.VRCHAT_PROC_NAME:
                    if p.info["create_time"] >= launch_time:
                        return p.info["pid"]
            time.sleep(1)

        return None

    def _find_window(self):
        result = None

        def callback(hwnd, _):
            nonlocal result
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == self.vrc_pid and win32gui.IsWindowVisible(hwnd):
                result = hwnd
                return False
            return True

        win32gui.EnumWindows(callback, None)
        return result
