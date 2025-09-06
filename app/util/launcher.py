import logging
from pathlib import Path
import subprocess
from typing import Optional

from app.model.vrchat import InstanceInfo


class VRCLauncher:
    VRCHAT_PATH = Path(
        r"C:/Program Files (x86)/Steam/steamapps/common/VRChat/VRChat.exe"
    )

    def __init__(self, vrchat_path: Path = VRCHAT_PATH):
        self.vrchat_path = vrchat_path

    def launch(
        self,
        instance: Optional[InstanceInfo] = None,
        no_vr: Optional[bool] = None,
        profile: Optional[int] = None,
        osc: Optional[str] = None,  # (inPort:outIP:outPort)
        fps: Optional[int] = None,
    ):
        args = [str(self.vrchat_path)]

        if instance:
            args.append(self.build_launch_url(instance))
        if profile:
            args.append(f"--profile={profile}")
        if no_vr:
            args.append("--no-vr")
        if osc:
            args.append(f"--osc={osc}")
        if fps:
            args.append(f"--fps={fps}")

        logging.info(f"Launching VRChat: {args}")
        try:
            subprocess.Popen(args)
        except Exception as e:
            logging.error(f"Failed to launch VRChat: {e}")

    @staticmethod
    def build_launch_url(instance: InstanceInfo) -> str:
        return f"vrchat://launch?ref=VRCQuickLauncher&id={instance.location}&shortName={instance.secureName}"
