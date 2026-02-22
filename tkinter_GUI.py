import os
import shutil
import glob
import threading
import subprocess
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkvideo import tkvideo
import sys

# 新的风格列表与映射（显示名 -> 代码）
STYLES = ["詹俊", "贺炜", "张路", "杨幂", "东方曜"]
STYLE_MAP = {
    "詹俊": "zhanjun",
    "贺炜": "hewei",
    "张路": "zhanglu",
    "杨幂": "yangmi",
    "东方曜": "yao",
}
DEFAULT_LANGUAGE = "汉语"  # 固定使用中文

INPUT_DIR = "input_videos"
OUTPUT_DIR = "output_videos"

class AIGCApp(tb.Window):
    def __init__(self):
        super().__init__(themename="cosmo")
        self.title("足球智能解说系统")
        self.geometry("1000x800")
        self.resizable(False, False)

        # 上传
        self.upload_btn = tb.Button(self, text="上传视频", bootstyle=PRIMARY, command=self.upload_video)
        self.upload_btn.pack(pady=15)

        # 风格
        tb.Label(self, text="请选择解说风格：", font=("微软雅黑", 14)).pack()
        self.style_var = tb.StringVar(value=STYLES[0])
        self.style_menu = tb.Combobox(self, textvariable=self.style_var, values=STYLES, state="readonly", font=("微软雅黑", 13))
        self.style_menu.pack(pady=5)

        # 状态
        self.status_label = tb.Label(self, text="", font=("微软雅黑", 13), bootstyle=INFO)
        self.status_label.pack(pady=5)

        # 生成按钮
        self.gen_btn = tb.Button(self, text="开始生成解说", bootstyle=SUCCESS, command=self.start_generate)
        self.gen_btn.pack(pady=15)

        # 视频展示
        self.video_frame = tb.Frame(self, width=960, height=540)
        self.video_frame.pack(pady=10)
        self.video_label = tb.Label(self.video_frame)
        self.video_label.pack()
        self.fullscreen_btn = tb.Button(self, text="全屏播放", bootstyle=WARNING, command=self.fullscreen_play)
        self.fullscreen_btn.pack(pady=5)
        self.current_video = None

    def upload_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mov;*.mkv;*.flv")])
        if file_path:
            os.makedirs(INPUT_DIR, exist_ok=True)
            dest_path = os.path.join(INPUT_DIR, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            messagebox.showinfo("上传成功", f"视频已保存到 {dest_path}")

    def get_latest_video(self):
        files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
        if not files:
            return None
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return files[0]

    def play_video(self, video_path):
        self.current_video = video_path
        self.video_label.config(image="")  # 清空
        self.player = tkvideo(video_path, self.video_label, loop=1, size=(960, 540))
        self.player.play()

    def fullscreen_play(self):
        if not self.current_video:
            messagebox.showwarning("提示", "请先生成并播放视频")
            return
        # 用系统播放器全屏播放
        if os.name == "nt":
            os.startfile(self.current_video)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.current_video])
        else:
            subprocess.Popen(["xdg-open", self.current_video])

    def start_generate(self):
        language = DEFAULT_LANGUAGE  # 固定使用中文
        style_display = self.style_var.get()
        # 映射为代码（传入子进程）
        style_code = STYLE_MAP.get(style_display, style_display)
        self.status_label.config(text="正在生成解说，请稍候...", bootstyle=INFO)
        self.gen_btn.config(state="disabled")
        def task():
            success = self.run_aigc(language, style_code)
            self.after(100, lambda: self.on_finish(success, style_code))
        threading.Thread(target=task, daemon=True).start()

    def run_aigc(self, language, style_code):
        env = os.environ.copy()
        env["AIGC_LANGUAGE"] = language
        env["AIGC_STYLE"] = style_code
        env['PYTHONIOENCODING'] = 'utf-8'  # 设置编码
        env['PYTHONUTF8'] = '1'  # 强制使用UTF-8
        
        try:
            result = subprocess.run(["python", "run_AIGC.py"], 
                                  check=True, env=env, 
                                  capture_output=True, timeout=600)  # 10分钟超时
            
            stdout_text = ""
            stderr_text = ""
            try:
                stdout_text = result.stdout.decode('utf-8', errors='replace')
                stderr_text = result.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                try:
                    stdout_text = result.stdout.decode('gbk', errors='replace')
                    stderr_text = result.stderr.decode('gbk', errors='replace')
                except UnicodeDecodeError:
                    stdout_text = result.stdout.decode('latin-1', errors='replace')
                    stderr_text = result.stderr.decode('latin-1', errors='replace')
            
            print(stdout_text)
            if stderr_text:
                print(f"错误输出: {stderr_text}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"子进程错误: {e}")
            try:
                if hasattr(e, 'stderr') and e.stderr:
                    error_text = e.stderr.decode('utf-8', errors='replace')
                    print(f"错误输出: {error_text}")
            except:
                pass
            return False
        except subprocess.TimeoutExpired:
            print("运行超时")
            return False
        except UnicodeDecodeError as e:
            print(f"编码错误: {e}")
            return False
        except Exception as e:
            print(f"其他错误: {e}")
            return False

    def run_football_voice(self):
        """
        如果存在 football_voice/convert.py，则运行之以把 football_comment/*.txt 转为音频；
        否则尝试以模块方式运行 football_voice。
        任何错误均只打印日志，不抛出。
        """
        cwd = os.getcwd()
        convert_py = os.path.join(cwd, "football_voice", "convert.py")
        try:
            if os.path.isfile(convert_py):
                print("检测到 football_voice/convert.py，开始转换 football_comment/*.txt 为音频...")
                result = subprocess.run(["python", convert_py], capture_output=True, timeout=300)
                try:
                    print(result.stdout.decode('utf-8', errors='replace'))
                    if result.stderr:
                        print(result.stderr.decode('utf-8', errors='replace'))
                except:
                    print(result.stdout)
                return True
            else:
                print("尝试以模块方式运行 football_voice...")
                result = subprocess.run(["python", "-m", "football_voice"], capture_output=True, timeout=300)
                try:
                    print(result.stdout.decode('utf-8', errors='replace'))
                    if result.stderr:
                        print(result.stderr.decode('utf-8', errors='replace'))
                except:
                    print(result.stdout)
                return True
        except Exception as e:
            print(f"football_voice 转换失败: {e}")
            return False

    def on_finish(self, success, style_code=None):
        self.gen_btn.config(state="normal")
        if success:
            self.status_label.config(text="生成完成！", bootstyle=SUCCESS)
            # 异步触发 football_voice 转换（不阻塞 UI）
            threading.Thread(target=self.run_football_voice, daemon=True).start()
            latest_video = self.get_latest_video()
            if latest_video:
                self.play_video(latest_video)
            else:
                self.status_label.config(text="未找到生成视频", bootstyle=WARNING)
        else:
            self.status_label.config(text="生成失败，请检查日志！", bootstyle=DANGER)

if __name__ == "__main__":
    app = AIGCApp()
    app.mainloop()