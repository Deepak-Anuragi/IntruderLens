"""
IntruderLens - Native Windows Service Wrapper
Allows running IntruderLens as a native background Windows Service via pywin32.
"""

import sys
import os
import time
from pathlib import Path

# Ensure user site-packages and pywin32 DLL directories are available in Service context
for user_site in Path("C:/Users").glob("*/AppData/Roaming/Python/Python*/site-packages"):
    if user_site.is_dir():
        site_str = str(user_site)
        if site_str not in sys.path:
            sys.path.insert(0, site_str)
        for sub in ("win32", "win32/lib", "pythonwin"):
            sub_path = str(user_site / sub)
            if sub_path not in sys.path:
                sys.path.insert(0, sub_path)
        dll_dir = user_site / "pywin32_system32"
        if dll_dir.is_dir() and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(dll_dir))
            except Exception:
                pass

import servicemanager
import win32serviceutil
import win32service
import win32event

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import intruder_lens
import config


class IntruderLensService(win32serviceutil.ServiceFramework):
    _svc_name_ = "IntruderLens"
    _svc_display_name_ = "IntruderLens Physical Security Daemon"
    _svc_description_ = "Monitors failed Windows logon attempts and captures intruder webcam photographs."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

    def SvcStop(self):
        """Called by SCM when stopping the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        servicemanager.LogInfoMsg("IntruderLens Service stop signal received.")
        self.is_running = False
        intruder_lens.RUNNING = False
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        """Main execution entry point for the service."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        self.main()

    def main(self):
        intruder_lens.logger.info("IntruderLens Windows Service is initializing...")
        intruder_lens.secure_directories()

        listener = intruder_lens.WindowsSecurityEventListener()
        listener.initialize_watermark()

        intruder_lens.logger.info("IntruderLens Service loop entered.")

        while self.is_running and intruder_lens.RUNNING:
            listener.poll_events()
            # Wait for stop event or poll interval timeout
            rc = win32event.WaitForSingleObject(self.stop_event, int(config.POLL_INTERVAL_SECONDS * 1000))
            if rc == win32event.WAIT_OBJECT_0:
                break

        intruder_lens.logger.info("IntruderLens Service loop terminated.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(IntruderLensService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(IntruderLensService)
