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


@dataclass(frozen=True)
class OscConfig:
    in_port: int
    out_ip: str
    out_port: int


@dataclass(frozen=True)
class LaunchOptions:
    instance: Optional[InstanceInfo] = None
    no_vr: bool = True
    fps: Optional[int] = None
    midi: Optional[str] = None
    osc: Optional[OscConfig] = None
    affinity: Optional[str] = None
    process_priority: Optional[str] = None
    watch_worlds: bool = False
    watch_avatars: bool = False
    debug_gui: bool = False
    sdk_log_levels: bool = False
    udon_debug_logging: bool = False
    extra_args: Optional[list[str]] = None


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    create_time: float


class VRCLauncher:
    LAUNCHER_PATH: Final[Path] = Path(
        r"C:/Program Files (x86)/Steam/steamapps/common/VRChat/launch.exe"
    )
    VRCHAT_PROC_NAME: Final[str] = "VRChat.exe"
    LAUNCH_TIMEOUT: Final[int] = 30

    @property
    def is_running(self) -> bool:
        return self.get_attached_process() is not None

    def __init__(
        self,
        profile: int,
        launcher_path: Path = LAUNCHER_PATH,
        launch_timeout: int = LAUNCH_TIMEOUT,
        manage_process: bool = True,
    ):
        self.launcher_path: Path = launcher_path
        self.profile: int = profile
        self.launch_timeout: int = launch_timeout
        self.manage_process: bool = manage_process
        self._proc: Optional[ProcessIdentity] = None

        if not self.launcher_path.exists():
            raise FileNotFoundError(
                f"VRChat launcher not found at {self.launcher_path}"
            )

        if self.manage_process:
            self._rollup_exist_process()

    def launch(self, options: LaunchOptions):
        args = [str(self.launcher_path), f"--profile={self.profile}"]

        # Target instance
        if options.instance:
            args.append(self._build_launch_url(options.instance))

        # Basic options
        if options.no_vr:
            args.append("--no-vr")
        if options.fps:
            args.append(f"--fps={options.fps}")
        if options.midi:
            args.append(f"--midi={options.midi}")
        if options.osc:
            args.append(
                f"--osc={options.osc.in_port}:{options.osc.out_ip}:{options.osc.out_port}"
            )

        # Performance options
        if options.affinity:
            args.append(f"--affinity={options.affinity}")
        if options.process_priority:
            args.append(f"--process-priority={options.process_priority}")

        # Debug options
        if options.watch_avatars:
            args.append("--watch-avatars")
        if options.watch_worlds:
            args.append("--watch-worlds")
        if options.debug_gui:
            args.append("--enable-debug-gui")
        if options.sdk_log_levels:
            args.append("--enable-sdk-log-levels")
        if options.udon_debug_logging:
            args.append("--enable-udon-debug-logging")

        # Extra args
        if options.extra_args:
            args.extend(options.extra_args)

        try:
            logging.debug(f"Launch args: {args[1:]}")
            launch_time = time.time()
            proc = subprocess.Popen(args)
            logging.debug(f"Launcher started (PID={proc.pid})")

            if self.manage_process:
                self._proc = self._wait_for_vrchat_process(launch_time)
                if not self._proc:
                    logging.error("VRChat.exe was not detected after launch")
                    return

            logging.info(
                f"VRChat started and attached (PID={self._proc.pid}) for profile No.{self.profile}"
            )
        except Exception as e:
            logging.error(f"Failed to launch VRChat: {e}")

    def terminate(self, timeout: int = 15) -> bool:
        process = self.get_attached_process()
        if not process:
            logging.debug("VRChat process already terminated")
            self._proc = None
            return True

        try:
            hwnd = self._find_window(process.pid)
            if hwnd:
                # ウィンドウがあればWM_CLOSEでの終了を試みる
                logging.debug(f"Sending WM_CLOSE to hwnd={hwnd} (PID={process.pid})")
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

                # プロセスの終了を待機、タイムアウト時は強制終了
                try:
                    process.wait(timeout=timeout)
                    logging.debug(
                        f"VRChat process (PID={process.pid}) exited after WM_CLOSE"
                    )
                except psutil.NoSuchProcess:
                    logging.debug(
                        f"VRChat process (PID={process.pid}) already exited after WM_CLOSE"
                    )
                except psutil.TimeoutExpired:
                    logging.warning(
                        f"VRChat process (PID={process.pid}) did not exit in {timeout}s, forcing terminate"
                    )
                    self._force_kill(process)
            else:
                # ウィンドウがない場合は強制終了
                logging.warning(
                    f"No visible window found for VRChat (PID={process.pid}), forcing terminate"
                )
                self._force_kill(process)
        except Exception as e:
            logging.error(f"Unexpected error occured: {e}")

        alive = self.get_attached_process() is None

        if not alive:
            self._proc = None

        return alive

    def _force_kill(self, process: psutil.Process, timeout: int = 15):
        try:
            process.kill()
            process.wait(timeout)
        except psutil.NoSuchProcess:
            logging.debug(f"VRChat process (PID={process.pid}) already terminated")
        except psutil.TimeoutExpired:
            logging.error(
                f"VRChat process (PID={process.pid}) still alive after kill wait timeout"
            )

    def get_attached_process(self, tol: float = 0.5) -> Optional[psutil.Process]:
        if not self._proc:
            return None
        try:
            p = psutil.Process(self._proc.pid)
            if (
                p.is_running()
                and p.name() == self.VRCHAT_PROC_NAME
                and abs(p.create_time() - self._proc.create_time) <= tol
            ):
                return p
        except psutil.NoSuchProcess:
            return None
        return None

    def _build_launch_url(self, instance: InstanceInfo) -> str:
        return (
            f"vrchat://launch?"
            f"ref=VRCQuickLauncher"
            f"&id={instance.id}"
            f"&shortName={instance.short_name}"
        )

    def _rollup_exist_process(self):
        logging.debug(f"Scanning processes for VRChat profile No.{self.profile}")

        matched: list[ProcessIdentity] = []
        for proc in psutil.process_iter(
            attrs=["pid", "name", "cmdline", "create_time"]
        ):
            if proc.info["name"] == self.VRCHAT_PROC_NAME:
                cmdline = proc.info.get("cmdline") or []
                if f"--profile={self.profile}" in cmdline:
                    matched.append(
                        ProcessIdentity(proc.info["pid"], proc.info["create_time"])
                    )

        if len(matched) >= 1:
            # 最初に見つかったものにのみアタッチ
            self._proc = matched[0]
            if len(matched) == 1:
                logging.info(
                    f"Attached to VRChat process (PID={self._proc.pid}) for profile No.{self.profile}"
                )
            else:
                others = [m.pid for m in matched[1:]]
                logging.warning(
                    f"Multiple VRChat processes for profile No.{self.profile}; "
                    f"attached to PID={self._proc.pid}, others={others}"
                )
                logging.warning(
                    f"Launching multiple instances with the same profile will not function correctly"
                )
        else:
            logging.debug(
                f"No existing VRChat process found for profile No.{self.profile}"
            )

    def _wait_for_vrchat_process(self, launch_time: float) -> Optional[ProcessIdentity]:
        start = time.monotonic()
        while time.monotonic() - start < self.launch_timeout:
            for p in psutil.process_iter(
                attrs=["pid", "name", "create_time", "cmdline"]
            ):
                if p.info["name"] == self.VRCHAT_PROC_NAME:
                    if p.info["create_time"] >= launch_time:
                        cmdline = p.info.get("cmdline") or []
                        if f"--profile={self.profile}" in cmdline:
                            return ProcessIdentity(p.info["pid"], p.info["create_time"])
            time.sleep(1)

        return None

    @staticmethod
    def _find_window(pid: int) -> Optional[int]:
        result = None

        def callback(hwnd: int, _):
            nonlocal result
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == pid and win32gui.IsWindowVisible(hwnd):
                result = hwnd
                return False
            return True

        win32gui.EnumWindows(callback, None)
        return result
