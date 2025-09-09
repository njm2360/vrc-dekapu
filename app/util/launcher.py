from typing_extensions import Final
import psutil
import logging
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from app.model.vrchat import InstanceInfo


@dataclass
class OscConfig:
    in_port: int
    out_ip: str
    out_port: int


class VRCLauncher:
    VRCHAT_PATH: Final[Path] = Path(
        r"C:/Program Files (x86)/Steam/steamapps/common/VRChat/launch.exe"
    )
    VRCHAT_PROC_NAME: Final[str] = "VRChat.exe"

    def __init__(self, profile: int, vrchat_path: Path = VRCHAT_PATH):
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

    def launch(
        self,
        instance: Optional[InstanceInfo] = None,
        no_vr: bool = True,
        osc: Optional[OscConfig] = None,
        fps: Optional[int] = None,
        midi: Optional[str] = None,
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

        logging.debug(f"Launching VRChat: {args}")
        try:
            self.vrc_pid = subprocess.Popen(args).pid
        except Exception as e:
            logging.error(f"Failed to launch VRChat: {e}")

    def terminate(self):
        if self.vrc_pid:
            try:
                subprocess.run(["taskkill", "/PID", str(self.vrc_pid)])
                psutil.Process(self.vrc_pid).wait(timeout=10)
                logging.debug(f"VRChat process (PID={self.vrc_pid}) terminated")
            except Exception as e:
                logging.error(f"Failed to terminate VRChat: {e}")
            finally:
                self.vrc_pid = None

    @property
    def is_running(self) -> bool:
        return self.vrc_pid is not None and psutil.pid_exists(self.vrc_pid)

    @staticmethod
    def build_launch_url(instance: InstanceInfo) -> str:
        return (
            f"vrchat://launch?ref=VRCQuickLauncher&id={instance.location}"
            f"&shortName={instance.short_name}"
        )
