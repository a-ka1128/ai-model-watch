from __future__ import annotations

import os
import subprocess
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


ROOT = Path(__file__).resolve().parent
STORAGE = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "AI_Model_Watch"
LOG_DIR = STORAGE / "logs"
TASK_BACKEND = r"AI Model Watch - Backend"
TASK_FRONTEND = r"AI Model Watch - Frontend"
TASK_WEEKLY = r"AI Model Watch - Weekly Pipeline"


class ControlPanel(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AI Model Watch Control Panel")
        self.geometry("720x560")
        self.minsize(620, 460)
        self.configure(bg="#eeeeee")
        self.status_var = tk.StringVar(value="확인 중...")
        self.detail_var = tk.StringVar(value="")
        self._build_ui()
        self.after(700, self.refresh)

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#eeeeee", padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="AI Model Watch", font=("Segoe UI", 16, "bold"), bg="#eeeeee").pack(side="left")
        tk.Label(header, textvariable=self.status_var, font=("Segoe UI", 11, "bold"), bg="#eeeeee", fg="#198754").pack(side="right")

        controls = tk.Frame(self, bg="#eeeeee", padx=18)
        controls.pack(fill="x")
        for label, command in (("시작", self.start), ("중지", self.stop), ("재시작", self.restart), ("수집 실행", self.collect_now), ("사이트 열기", self.open_site), ("로그 폴더", self.open_logs)):
            tk.Button(controls, text=label, command=command, width=11, relief="groove").pack(side="left", padx=(0, 8))

        info = tk.Frame(self, bg="#eeeeee", padx=18, pady=12)
        info.pack(fill="x")
        tk.Label(info, textvariable=self.detail_var, anchor="w", bg="#eeeeee", fg="#555555").pack(fill="x")
        tk.Label(info, text=f"Website: http://127.0.0.1:3000    API: http://127.0.0.1:8000    Logs: {LOG_DIR}", anchor="w", bg="#eeeeee", fg="#555555").pack(fill="x")

        tk.Label(self, text="로그 (backend + frontend + weekly)", anchor="w", bg="#eeeeee", padx=18).pack(fill="x")
        frame = tk.Frame(self, bg="#eeeeee", padx=18, pady=4)
        frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(frame, bg="#111111", fg="#eeeeee", insertbackground="#eeeeee", wrap="word", state="disabled")
        scrollbar = tk.Scrollbar(frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _run_task(self, task: str, action: str) -> bool:
        result = subprocess.run(["schtasks.exe", action, "/TN", task], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            messagebox.showerror("작업 실행 실패", result.stderr.strip() or result.stdout.strip() or task)
            return False
        return True

    def start(self) -> None:
        self._run_task(TASK_BACKEND, "/Run")
        self._run_task(TASK_FRONTEND, "/Run")
        self.after(500, self.refresh)

    def stop(self) -> None:
        self._run_task(TASK_BACKEND, "/End")
        self._run_task(TASK_FRONTEND, "/End")
        self.after(500, self.refresh)

    def restart(self) -> None:
        self.stop()
        self.after(1200, self.start)

    def collect_now(self) -> None:
        if self._run_task(TASK_WEEKLY, "/Run"):
            self.detail_var.set("수집 작업을 시작했습니다. weekly.log에서 진행 상황을 확인하세요.")
            self.after(1000, self.refresh)

    @staticmethod
    def open_site() -> None:
        webbrowser.open("http://127.0.0.1:3000")

    @staticmethod
    def open_logs() -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(LOG_DIR)  # type: ignore[attr-defined]

    @staticmethod
    def _is_online(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=1.5):
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def refresh(self) -> None:
        threading.Thread(target=self._check_status, daemon=True).start()
        self._read_logs()
        self.after(3000, self.refresh)

    def _check_status(self) -> None:
        api = self._is_online("http://127.0.0.1:8000/health")
        website = self._is_online("http://127.0.0.1:3000")
        state = "가동 중 · 두 서비스 정상" if api and website else "부분 실행" if api or website else "중지됨"
        detail = f"API: {'정상' if api else '중지'}    Website: {'정상' if website else '중지'}"
        self.after(0, lambda: (self.status_var.set(state), self.detail_var.set(detail)))

    def _read_logs(self) -> None:
        chunks: list[str] = []
        for name in ("backend.log", "frontend.log", "weekly.log"):
            path = LOG_DIR / name
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")[-5000:]
                except OSError as exc:
                    text = f"{name}: {exc}"
                chunks.append(f"===== {name} =====\n{text}")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n\n".join(chunks) or "로그가 아직 없습니다.")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    ControlPanel().mainloop()
