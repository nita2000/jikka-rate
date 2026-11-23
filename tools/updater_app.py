"""実家じまいレート データ更新アプリ（Windows向け・標準ライブラリのみ）.

主な特徴:
- 起動時およびウィンドウ復帰時（<FocusIn>）に Downloads フォルダの最新Excelを自動スキャン
- Excel手動取り込みだけでなく、ワンクリックでの「e-Stat API＋最新公的データセット再生成＆本番公開」にも対応
- メモリ上のみの完全ドライラン検証＆差分プレビュー（キャンセルしてもローカルGitを汚さない）
- CREATE_NO_WINDOW + 非同期スレッド実行（黒い窓の点滅・画面フリーズゼロ）
- 失敗時のデータファイル限定自動ロールバック＆未プッシュコミット1クリック再送
"""

from __future__ import annotations

import ctypes
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

ROOT_DIR = Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT_DIR / "pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from fetch_jikka_stats import is_valid_jikka_excel, preview_jikka_excel_diff  # noqa: E402

ESTAT_PORTAL_URL = "https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00200522"
PROD_SITE_URL = "https://jikkarate.com/"
GITHUB_ACTIONS_URL = "https://github.com/nita2000/jikka-rate/actions"

DATA_PATHS_FOR_GIT = ["data/raw/jikka_cost_trends.csv", "site/src/data"]
CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_py_cli = Path(sys.executable).with_name("python.exe")
PYTHON_CLI = str(_py_cli if _py_cli.is_file() else Path(sys.executable))

# カラーテーマ（実家じまいレート 本番フォレストグリーンデザインと統一）
COLOR_BG = "#F8FAFC"
COLOR_CARD = "#FFFFFF"
COLOR_BORDER = "#E2E8F0"
COLOR_PRIMARY = "#047857"
COLOR_PRIMARY_HOVER = "#065F46"
COLOR_PRIMARY_LIGHT = "#ECFDF5"
COLOR_TEXT = "#0F172A"
COLOR_MUTED = "#475569"
COLOR_DANGER = "#B91C1C"
COLOR_DANGER_BG = "#FEF2F2"
COLOR_WARN = "#92400E"
COLOR_WARN_BG = "#FFFBEB"


def run_hidden_cmd(
    args: list[str],
    cwd: Path = ROOT_DIR,
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    """黒いコンソール窓を出さずにUTF-8でコマンドを実行する。"""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATION_FLAGS,
        env=env,
    )


def find_latest_jikka_excel(search_dirs: list[Path]) -> Path | None:
    """指定ディレクトリ群から更新日時が新しい実家じまいレート用Excelを1件見つける。"""
    candidates: list[Path] = []
    for folder in search_dirs:
        if not folder.is_dir():
            continue
        for p in folder.glob("*.xlsx"):
            if p.name.startswith("~$"):
                continue
            candidates.append(p)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates[:25]:
        if is_valid_jikka_excel(path):
            return path
    return None


def get_git_state() -> dict[str, Any]:
    """ローカルGitの変更状態と未プッシュ件数を返す。"""
    st = run_hidden_cmd(["git", "status", "--porcelain"])
    if st.returncode != 0:
        return {"ok": False, "error": st.stderr.strip() or "Git状態の取得に失敗しました"}

    other_dirty: list[str] = []
    data_dirty: list[str] = []
    for raw_line in st.stdout.splitlines():
        if not raw_line.strip():
            continue
        rel = raw_line[3:].strip().strip('"').replace("\\", "/")
        if rel == "data/raw/jikka_cost_trends.csv" or rel.startswith("site/src/data/"):
            data_dirty.append(rel)
        else:
            other_dirty.append(rel)

    ahead = 0
    ah = run_hidden_cmd(["git", "rev-list", "--count", "origin/main..HEAD"])
    if ah.returncode == 0 and ah.stdout.strip().isdigit():
        ahead = int(ah.stdout.strip())

    return {
        "ok": True,
        "other_dirty": other_dirty,
        "data_dirty": data_dirty,
        "ahead": ahead,
    }


def load_current_summary() -> dict[str, Any] | None:
    latest_path = ROOT_DIR / "site" / "src" / "data" / "latest.json"
    if not latest_path.is_file():
        return None
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except Exception:
        return None


class JikkaRateUpdaterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("実家じまいレート データ更新アプリ")
        self.root.geometry("760x710")
        self.root.minsize(680, 620)
        self.root.configure(bg=COLOR_BG)

        self.is_busy = False
        self.selected_excel: Path | None = None
        self.last_preview: dict[str, Any] | None = None
        self.last_downloads_sig: tuple[str, float] | None = None
        self.force_same_var = tk.BooleanVar(value=False)

        self.downloads_dir = Path.home() / "Downloads"
        self.search_dirs = [self.downloads_dir, ROOT_DIR / "data" / "raw" / "official_excel"]

        self._build_ui()
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.refresh_all(auto_detect=True)

    def _build_ui(self) -> None:
        font_title = ("Yu Gothic UI", 14, "bold")
        font_h2 = ("Yu Gothic UI", 10, "bold")
        font_body = ("Yu Gothic UI", 9)
        font_bold = ("Yu Gothic UI", 9, "bold")
        font_mono = ("Consolas", 9)

        header = tk.Frame(self.root, bg=COLOR_PRIMARY, height=58)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        h_inner = tk.Frame(header, bg=COLOR_PRIMARY)
        h_inner.pack(fill=tk.BOTH, expand=True, padx=18)
        tk.Label(
            h_inner,
            text="実家じまいレート  データ更新アプリ",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            font=font_title,
        ).pack(side=tk.LEFT, pady=12)
        tk.Label(
            h_inner,
            text="公的統計・解体単価 → 検証 → 本番自動公開",
            bg=COLOR_PRIMARY,
            fg="#D1FAE5",
            font=font_body,
        ).pack(side=tk.RIGHT, pady=16)

        container = tk.Frame(self.root, bg=COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # 1. 現在の本番データ状況カード
        status_card = tk.Frame(container, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        status_card.pack(fill=tk.X, pady=(0, 10))
        s_pad = tk.Frame(status_card, bg=COLOR_CARD)
        s_pad.pack(fill=tk.X, padx=14, pady=10)

        s_top = tk.Frame(s_pad, bg=COLOR_CARD)
        s_top.pack(fill=tk.X)
        tk.Label(s_top, text="現在の収録状況", bg=COLOR_CARD, fg=COLOR_PRIMARY, font=font_h2).pack(side=tk.LEFT)
        self.lbl_git_state = tk.Label(s_top, text="確認中...", bg=COLOR_CARD, fg=COLOR_MUTED, font=font_body)
        self.lbl_git_state.pack(side=tk.RIGHT)

        self.lbl_current_summary = tk.Label(
            s_pad,
            text="読み込み中...",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=font_bold,
            anchor="w",
            justify=tk.LEFT,
        )
        self.lbl_current_summary.pack(fill=tk.X, pady=(4, 0))

        self.retry_bar = tk.Frame(s_pad, bg=COLOR_WARN_BG, highlightbackground="#FCD34D", highlightthickness=1)
        self.lbl_retry_msg = tk.Label(
            self.retry_bar,
            text="",
            bg=COLOR_WARN_BG,
            fg=COLOR_WARN,
            font=font_bold,
        )
        self.lbl_retry_msg.pack(side=tk.LEFT, padx=10, pady=6)
        self.btn_retry_push = tk.Button(
            self.retry_bar,
            text="未公開コミットを再プッシュ",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=font_bold,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._start_retry_push,
        )
        self.btn_retry_push.pack(side=tk.RIGHT, padx=8, pady=4)

        # 2. STEP 1: データ取得・選択カード
        step1_card = tk.Frame(container, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        step1_card.pack(fill=tk.X, pady=(0, 10))
        s1 = tk.Frame(step1_card, bg=COLOR_CARD)
        s1.pack(fill=tk.X, padx=14, pady=10)

        tk.Label(
            s1,
            text="STEP 1｜公的統計ポータル確認 または 更新用Excelを選択",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=font_h2,
        ).pack(anchor="w")

        btn_row = tk.Frame(s1, bg=COLOR_CARD)
        btn_row.pack(fill=tk.X, pady=(8, 6))

        self.btn_open_estat = tk.Button(
            btn_row,
            text="① e-Stat 公的統計ページを開く",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            font=font_bold,
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: webbrowser.open(ESTAT_PORTAL_URL),
        )
        self.btn_open_estat.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_rescan = tk.Button(
            btn_row,
            text="再スキャン",
            bg="#F1F5F9",
            fg=COLOR_TEXT,
            activebackground="#E2E8F0",
            relief=tk.FLAT,
            font=font_bold,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self.refresh_all(auto_detect=True),
        )
        self.btn_rescan.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_browse = tk.Button(
            btn_row,
            text="手動でExcel選択...",
            bg="#FFFFFF",
            fg=COLOR_MUTED,
            activebackground="#F8FAFC",
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            relief=tk.FLAT,
            font=font_body,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._choose_file_dialog,
        )
        self.btn_browse.pack(side=tk.LEFT)

        self.lbl_selected_file = tk.Label(
            s1,
            text="対象Excel：未選択（Excelなしでもe-Stat/マスタ再計算＆公開が可能です）",
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            font=font_body,
            anchor="w",
        )
        self.lbl_selected_file.pack(fill=tk.X)

        # 3. STEP 2: 検証＆本番公開カード
        step2_card = tk.Frame(container, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        step2_card.pack(fill=tk.X, pady=(0, 10))
        s2 = tk.Frame(step2_card, bg=COLOR_CARD)
        s2.pack(fill=tk.X, padx=14, pady=10)

        tk.Label(
            s2,
            text="STEP 2｜データセット検証 ＆ 本番公開（GitHub push）",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=font_h2,
        ).pack(anchor="w")

        self.lbl_verdict = tk.Label(
            s2,
            text="マスタまたは統計データの再ビルド＆テストを実行して本番公開できます。",
            bg=COLOR_PRIMARY_LIGHT,
            fg=COLOR_PRIMARY_HOVER,
            font=font_bold,
            anchor="w",
            padx=10,
            pady=6,
        )
        self.lbl_verdict.pack(fill=tk.X, pady=(6, 6))

        self.lbl_diff_detail = tk.Label(
            s2,
            text="",
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
            font=font_body,
            anchor="w",
            justify=tk.LEFT,
        )
        self.lbl_diff_detail.pack(fill=tk.X)

        act_row = tk.Frame(s2, bg=COLOR_CARD)
        act_row.pack(fill=tk.X, pady=(10, 0))

        self.btn_publish = tk.Button(
            act_row,
            text="② データセット再生成・テスト検証 ＆ 本番公開（GitHub push）",
            bg=COLOR_PRIMARY,
            fg="#FFFFFF",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="#FFFFFF",
            disabledforeground="#94A3B8",
            relief=tk.FLAT,
            font=("Yu Gothic UI", 10, "bold"),
            padx=18,
            pady=9,
            cursor="hand2",
            command=self._start_publish,
        )
        self.btn_publish.pack(side=tk.LEFT)

        self.chk_force_same = tk.Checkbutton(
            act_row,
            text="同日データでも強制再実行する",
            variable=self.force_same_var,
            bg=COLOR_CARD,
            fg=COLOR_MUTED,
            activebackground=COLOR_CARD,
            font=font_body,
            command=self._update_publish_button_state,
        )
        self.chk_force_same.pack(side=tk.RIGHT)

        # 4. 実行ログカード
        log_card = tk.Frame(container, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        l_pad = tk.Frame(log_card, bg=COLOR_CARD)
        l_pad.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        tk.Label(l_pad, text="実行ログ", bg=COLOR_CARD, fg=COLOR_MUTED, font=font_h2).pack(anchor="w", pady=(0, 4))
        self.txt_log = scrolledtext.ScrolledText(
            l_pad,
            height=9,
            font=font_mono,
            bg="#0F172A",
            fg="#E2E8F0",
            insertbackground="#FFFFFF",
            relief=tk.FLAT,
            padx=8,
            pady=6,
            state=tk.DISABLED,
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        footer = tk.Frame(container, bg=COLOR_BG)
        footer.pack(fill=tk.X)
        for label, url in [
            ("本番サイトを開く (jikkarate.com)", PROD_SITE_URL),
            ("GitHub Actions を確認", GITHUB_ACTIONS_URL),
        ]:
            link = tk.Label(
                footer,
                text=f"↗ {label}",
                bg=COLOR_BG,
                fg=COLOR_PRIMARY,
                font=font_bold,
                cursor="hand2",
            )
            link.pack(side=tk.LEFT, padx=(0, 16))
            link.bind("<Button-1>", lambda _e, target=url: webbrowser.open(target))

    def _log(self, msg: str) -> None:
        ts = dt.datetime.now().strftime("%H:%M:%S")

        def append() -> None:
            self.txt_log.configure(state=tk.NORMAL)
            self.txt_log.insert(tk.END, f"[{ts}] {msg}\n")
            self.txt_log.see(tk.END)
            self.txt_log.configure(state=tk.DISABLED)

        self.root.after(0, append)

    def _on_focus_in(self, event: tk.Event[Any]) -> None:
        if event.widget is not self.root or self.is_busy:
            return
        latest_sig = self._get_downloads_signature()
        if latest_sig != self.last_downloads_sig:
            self.last_downloads_sig = latest_sig
            self.refresh_all(auto_detect=True)

    def _get_downloads_signature(self) -> tuple[str, float] | None:
        if not self.downloads_dir.is_dir():
            return None
        files = [p for p in self.downloads_dir.glob("*.xlsx") if not p.name.startswith("~$")]
        if not files:
            return None
        newest = max(files, key=lambda p: p.stat().st_mtime)
        return (newest.name, newest.stat().st_mtime)

    def _choose_file_dialog(self) -> None:
        if self.is_busy:
            return
        chosen = filedialog.askopenfilename(
            title="実家じまいレート 更新用Excelファイルを選択",
            initialdir=str(self.downloads_dir if self.downloads_dir.is_dir() else ROOT_DIR),
            filetypes=[("Excelファイル", "*.xlsx")],
        )
        if chosen:
            self.selected_excel = Path(chosen)
            self._run_dry_preview_async()

    def refresh_all(self, auto_detect: bool = False) -> None:
        if self.is_busy:
            return
        self.last_downloads_sig = self._get_downloads_signature()

        summary = load_current_summary()
        if summary:
            date_str = summary.get("date", "不明")
            nat = summary.get("national", {})
            self.lbl_current_summary.configure(
                text=(
                    f"最新基準日：{date_str}  ｜  "
                    f"全国木造解体 {nat.get('wood_man_per_tsubo', 0):.2f}万円/坪 / "
                    f"鉄骨 {nat.get('steel_man_per_tsubo', 0):.2f}万円/坪 / "
                    f"RC {nat.get('rc_man_per_tsubo', 0):.2f}万円/坪 / 空き家率 {nat.get('akiya_rate_pct', 13.8):.1f}%"
                )
            )
        else:
            self.lbl_current_summary.configure(text="現在のデータセット（latest.json）が見つかりません。")

        git_st = get_git_state()
        self.git_state = git_st
        self.retry_bar.pack_forget()
        if not git_st.get("ok"):
            self.lbl_git_state.configure(text=f"Git未初期化またはエラー", fg=COLOR_MUTED)
        elif git_st["other_dirty"]:
            self.lbl_git_state.configure(
                text=f"⚠ サイトコード未コミット {len(git_st['other_dirty'])}件あり",
                fg=COLOR_WARN,
            )
        elif git_st["ahead"] > 0:
            self.lbl_git_state.configure(text=f"未公開コミット {git_st['ahead']}件あり", fg=COLOR_WARN)
            self.lbl_retry_msg.configure(
                text=f"前回プッシュ未完了のコミットが {git_st['ahead']} 件残っています。"
            )
            self.retry_bar.pack(fill=tk.X, pady=(8, 0))
        else:
            self.lbl_git_state.configure(text="✓ Gitワーキングツリー正常", fg=COLOR_PRIMARY)

        if auto_detect:
            found = find_latest_jikka_excel(self.search_dirs)
            self.selected_excel = found
            if found:
                self._run_dry_preview_async()
            else:
                self.last_preview = None
                self.lbl_selected_file.configure(
                    text="対象Excel：未選択（そのまま②ボタンでe-Stat/マスタから再生成＆テスト可能です）",
                    fg=COLOR_MUTED,
                )
                self._update_publish_button_state()

    def _run_dry_preview_async(self) -> None:
        target = self.selected_excel
        if target is None:
            return
        mtime = dt.datetime.fromtimestamp(target.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        self.lbl_selected_file.configure(
            text=f"対象Excel：{target.name}（更新：{mtime} / 場所：{target.parent.name}）",
            fg=COLOR_TEXT,
        )
        self.lbl_verdict.configure(text="Excelを検証中（メモリ上ドライラン）...", bg=COLOR_BG, fg=COLOR_MUTED)
        self.lbl_diff_detail.configure(text="")
        self.last_preview = None
        self._update_publish_button_state()

        def worker() -> None:
            try:
                if not is_valid_jikka_excel(target):
                    raise ValueError("対象のシート（木造・解体・空き家）が見つかりません。")
                info = preview_jikka_excel_diff(target)
                self.root.after(0, lambda: self._render_preview_result(info, None))
            except Exception as exc:
                err_msg = str(exc)
                self.root.after(0, lambda: self._render_preview_result(None, err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _render_preview_result(self, info: dict[str, Any] | None, err: str | None) -> None:
        if err or info is None:
            self.last_preview = None
            self.lbl_verdict.configure(text=f"❌ 検証エラー：{err}", bg=COLOR_DANGER_BG, fg=COLOR_DANGER)
            self._log(f"[ERROR] プレビュー検証失敗: {err}")
            self._update_publish_button_state()
            return

        self.last_preview = info
        status = info["status"]
        cur_d = info["current_latest_date"] or "なし"
        new_d = info["new_latest_date"]
        if status == "newer":
            self.lbl_verdict.configure(
                text=f"✅ 更新可能です（最新期を追加：+{info['added_periods']}期 / {cur_d} → {new_d}）",
                bg=COLOR_PRIMARY_LIGHT,
                fg=COLOR_PRIMARY_HOVER,
            )
        else:
            self.lbl_verdict.configure(
                text=f"ℹ️ 選択ファイル基準日: {new_d}（現在: {cur_d}）",
                bg=COLOR_WARN_BG,
                fg=COLOR_WARN,
            )
        self._update_publish_button_state()

    def _update_publish_button_state(self) -> None:
        if self.is_busy:
            self.btn_publish.configure(state=tk.DISABLED, bg="#CBD5E1")
            return
        self.btn_publish.configure(state=tk.NORMAL, bg=COLOR_PRIMARY)

    def _set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in (self.btn_rescan, self.btn_browse, self.btn_retry_push):
            btn.configure(state=state)
        self._update_publish_button_state()

    def _rollback_data_files(self) -> None:
        self._log("データファイルを更新前へ自動ロールバックします...")
        run_hidden_cmd(["git", "checkout", "--", *DATA_PATHS_FOR_GIT])

    def _start_retry_push(self) -> None:
        if self.is_busy:
            return
        self._set_busy(True)
        self._log("未公開コミットの再プッシュを開始します...")

        def worker() -> None:
            try:
                res = run_hidden_cmd(["git", "push", "origin", "main"], timeout=120)
                if res.returncode != 0:
                    raise RuntimeError(res.stderr.strip() or res.stdout.strip() or "git push に失敗しました")
                self._log("✅ 再プッシュが完了しました。")
                self.root.after(0, lambda: messagebox.showinfo("公開完了", "未公開コミットのプッシュが完了しました！"))
            except Exception as exc:
                self._log(f"❌ 再プッシュ失敗: {exc}")
                self.root.after(0, lambda err=str(exc): messagebox.showerror("プッシュ失敗", f"再プッシュに失敗しました：\n{err}"))
            finally:
                self.root.after(0, lambda: (self._set_busy(False), self.refresh_all(auto_detect=False)))

        threading.Thread(target=worker, daemon=True).start()

    def _start_publish(self) -> None:
        if self.is_busy:
            return
        excel_path = self.selected_excel
        self._set_busy(True)
        self._log("=== データセット更新・テスト検証を開始します ===")

        def worker() -> None:
            mutated_data = False
            committed = False
            try:
                self._log("[1/4] 公的統計・解体単価データ取得中...")
                mutated_data = True
                cmd = [PYTHON_CLI, str(PIPELINE_DIR / "fetch_jikka_stats.py")]
                if excel_path is not None:
                    cmd.extend(["--excel", str(excel_path)])
                f_res = run_hidden_cmd(cmd, timeout=90)
                if f_res.returncode != 0:
                    raise RuntimeError(f"統計データ取得失敗:\n{f_res.stderr.strip() or f_res.stdout.strip()}")
                for line in f_res.stdout.strip().splitlines():
                    self._log(f"  {line}")

                self._log("[2/4] サイト用JSONデータセット生成中...")
                b_res = run_hidden_cmd([PYTHON_CLI, str(PIPELINE_DIR / "build_datasets.py")], timeout=90)
                if b_res.returncode != 0:
                    raise RuntimeError(f"データセット生成失敗:\n{b_res.stderr.strip() or b_res.stdout.strip()}")
                for line in b_res.stdout.strip().splitlines():
                    self._log(f"  {line}")

                self._log("[3/4] パイプライン自動テスト実行中...")
                t_res = run_hidden_cmd(
                    [PYTHON_CLI, "-m", "unittest", "discover", "-s", "pipeline/tests", "-v"],
                    timeout=90,
                )
                if t_res.returncode != 0:
                    raise RuntimeError(f"単体テスト失敗:\n{t_res.stderr.strip() or t_res.stdout.strip()}")
                self._log("  ✓ 全単体テスト合格")

                gs = get_git_state()
                if not gs.get("ok"):
                    self._log("✅ ローカルデータセットの更新と全単体テストが完了しました（Gitリポジトリ未接続のためpushはスキップ）。")
                    return

                self._log("[4/4] GitHubへコミット＆プッシュ中...")
                add_res = run_hidden_cmd(["git", "add", "--", *DATA_PATHS_FOR_GIT])
                if add_res.returncode != 0:
                    raise RuntimeError(f"git add 失敗: {add_res.stderr.strip()}")

                diff_res = run_hidden_cmd(["git", "diff", "--cached", "--quiet"])
                if diff_res.returncode == 0:
                    self._log("ℹ️ データに差分がなかったため、コミットをスキップしました。")
                    self.root.after(0, lambda: messagebox.showinfo("変更なし", "すでに最新データと完全一致しています。"))
                    return

                today_str = dt.date.today().isoformat()
                commit_msg = f"chore(data): 実家じまい・解体・空き家相場データを更新（{today_str}）"
                c_res = run_hidden_cmd(["git", "commit", "-m", commit_msg])
                if c_res.returncode != 0:
                    raise RuntimeError(f"git commit 失敗:\n{c_res.stderr.strip() or c_res.stdout.strip()}")
                committed = True
                mutated_data = False

                p_res = run_hidden_cmd(["git", "push", "origin", "main"], timeout=120)
                if p_res.returncode != 0:
                    raise RuntimeError(
                        "コミットは成功しましたが git push に失敗しました:\n"
                        + (p_res.stderr.strip() or p_res.stdout.strip())
                    )

                self._log("✅ 公開完了！データを本番へプッシュしました。")
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "本番公開完了",
                        "データ更新＆GitHubプッシュが完了しました！\n約1〜2分で Cloudflare Pages が自動ビルドされ、jikkarate.com に反映されます。",
                    ),
                )
            except Exception as exc:
                err_text = str(exc)
                self._log(f"❌ エラー発生: {err_text}")
                if mutated_data and not committed:
                    self._rollback_data_files()
                self.root.after(0, lambda msg=err_text: messagebox.showerror("更新エラー", msg))
            finally:
                self.root.after(0, lambda: (self._set_busy(False), self.refresh_all(auto_detect=False)))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    JikkaRateUpdaterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
