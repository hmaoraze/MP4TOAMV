import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')

class VideoConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频转换工具 - MP4转AMV")
        self.root.geometry("550x420")
        self.root.resizable(False, False)
        
        self.convert_lock = threading.Lock()
        self.is_converting = False
        self.current_process = None
        self.selected_files = []
        
        self._create_widgets()
        
    def _create_widgets(self):
        header_frame = tk.Frame(self.root)
        header_frame.pack(pady=10)
        
        self.title_label = tk.Label(header_frame, text="视频转换工具 - MP4转AMV", font=("Microsoft YaHei UI", 16, "bold"))
        self.title_label.pack()
        
        self.status_label = tk.Label(self.root, text="就绪", fg="blue", font=("Microsoft YaHei UI", 9))
        self.status_label.pack(pady=5)
        
        self.select_button = tk.Button(
            self.root, 
            text="📁 选择视频文件", 
            command=self.select_files,
            font=("Microsoft YaHei UI", 10),
            width=20,
            height=1
        )
        self.select_button.pack(pady=10)
        
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=5)
        
        tk.Label(file_frame, text="已选文件:", font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        self.file_count_label = tk.Label(file_frame, text="0", fg="blue", font=("Microsoft YaHei UI", 9, "bold"))
        self.file_count_label.pack(side=tk.LEFT)
        
        self.convert_button = tk.Button(
            self.root, 
            text="▶ 开始转换", 
            state=tk.DISABLED, 
            command=self.start_conversion_thread,
            font=("Microsoft YaHei UI", 10, "bold"),
            width=20,
            height=1,
            bg="#4CAF50",
            fg="white"
        )
        self.convert_button.pack(pady=10)
        
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=10, fill=tk.X, padx=30)
        
        tk.Label(progress_frame, text="总进度:", font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        self.total_progress = ttk.Progressbar(progress_frame, mode='determinate', length=480)
        self.total_progress.pack(pady=5)
        self.total_percent_label = tk.Label(progress_frame, text="0%", font=("Microsoft YaHei UI", 9))
        self.total_percent_label.pack()
        
        tk.Label(progress_frame, text="当前文件:", font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        self.file_progress = ttk.Progressbar(progress_frame, mode='indeterminate', length=480)
        self.file_progress.pack(pady=5)
        self.file_progress.stop()
        
        self.current_file_label = tk.Label(
            progress_frame, 
            text="无", 
            fg="gray", 
            font=("Microsoft YaHei UI", 9),
            wraplength=480
        )
        self.current_file_label.pack(pady=5)
        
        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(log_frame, text="转换日志:", font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)
        
        self.progress_text = tk.Text(log_frame, height=10, width=60, font=("Consolas", 8))
        scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=scrollbar.set)
        
        self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def select_files(self):
        if self.is_converting:
            messagebox.showwarning("警告", "转换进行中，请等待完成！")
            return
            
        self.selected_files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")]
        )
        
        if self.selected_files:
            valid_files = []
            for file in self.selected_files:
                if os.path.exists(file):
                    valid_files.append(file)
                else:
                    self._log_message(f"⚠ 跳过不存在的文件: {file}")
            
            self.selected_files = valid_files
            
            if self.selected_files:
                self.convert_button.config(state=tk.NORMAL)
                count = len(self.selected_files)
                self.file_count_label.config(text=str(count))
                self._log_message(f"已选择 {count} 个有效文件")
                self._update_status(f"已加载 {count} 个文件")
            else:
                self.file_count_label.config(text="0")
                messagebox.showinfo("信息", "没有选择有效的视频文件")
    
    def start_conversion_thread(self):
        if not self.selected_files:
            messagebox.showerror("错误", "请先选择视频文件！")
            return
        
        with self.convert_lock:
            if self.is_converting:
                messagebox.showwarning("警告", "转换任务正在进行中！")
                return
            self.is_converting = True
        
        self.convert_button.config(state=tk.DISABLED, bg="#888888")
        self.select_button.config(state=tk.DISABLED)
        
        self.total_progress['value'] = 0
        self.total_percent_label.config(text="0%")
        
        conversion_thread = threading.Thread(target=self.convert_videos, daemon=True)
        conversion_thread.start()
    
    def convert_videos(self):
        success_count = 0
        fail_count = 0
        total_files = len(self.selected_files)
        
        for index, input_file in enumerate(self.selected_files):
            if not os.path.exists(input_file):
                self._log_message(f"❌ 文件不存在: {input_file}")
                fail_count += 1
                self._update_total_progress(index + 1, total_files)
                continue
            
            output_file = os.path.splitext(input_file)[0] + ".amv"
            file_name = os.path.basename(input_file)
            
            self._update_current_file(file_name)
            self._log_message(f"📼 正在转换 [{index + 1}/{total_files}]: {file_name}")
            self._start_file_progress()
            
            try:
                command = [
                    ffmpeg_path,
                    "-i", input_file,
                    "-c:v", "amv",
                    "-c:a", "adpcm_ima_amv",
                    "-ar", "22050",
                    "-ac", "1",
                    "-r", "15",
                    "-block_size", "1470",
                    "-vf", "scale=160:120,format=yuvj420p",
                    "-strict", "experimental",
                    "-y", output_file
                ]
                
                self.current_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = self.current_process.communicate()
                
                if self.current_process.returncode == 0:
                    output_name = os.path.basename(output_file)
                    self._log_message(f"✅ 转换成功: {file_name} → {output_name}")
                    success_count += 1
                else:
                    error_msg = self._extract_error(stderr)
                    self._log_message(f"❌ 转换失败: {file_name} - {error_msg}")
                    fail_count += 1
                    
            except Exception as e:
                self._log_message(f"💥 执行错误: {file_name} - {str(e)}")
                fail_count += 1
            finally:
                self._stop_file_progress()
                self.current_process = None
                self._update_total_progress(index + 1, total_files)
        
        self._finalize_conversion(success_count, fail_count, total_files)
    
    def _extract_error(self, stderr):
        if not stderr:
            return "未知错误"
        
        lines = stderr.strip().split('\n')
        error_lines = [line for line in lines if 'error' in line.lower() or 'invalid' in line.lower()]
        
        if error_lines:
            return error_lines[0].strip()
        
        return lines[-1].strip() if lines else "未知错误"
    
    def _update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))
    
    def _update_current_file(self, filename):
        self.root.after(0, lambda: self.current_file_label.config(text=filename, fg="blue"))
    
    def _start_file_progress(self):
        self.root.after(0, lambda: self.file_progress.start(50))
    
    def _stop_file_progress(self):
        self.root.after(0, lambda: self.file_progress.stop())
    
    def _update_total_progress(self, current, total):
        percentage = (current / total) * 100
        self.root.after(0, lambda: self.total_progress.config(value=percentage))
        self.root.after(0, lambda: self.total_percent_label.config(text=f"{percentage:.1f}%"))
    
    def _log_message(self, message):
        def _update():
            self.progress_text.insert(tk.END, message + "\n")
            self.progress_text.see(tk.END)
        self.root.after(0, _update)
    
    def _finalize_conversion(self, success, failed, total):
        def _finish():
            self.is_converting = False
            self.convert_button.config(state=tk.NORMAL, bg="#4CAF50")
            self.select_button.config(state=tk.NORMAL)
            
            if success > 0:
                self._update_status(f"✅ 完成 - 成功: {success}, 失败: {failed}")
            else:
                self._update_status("❌ 全部失败")
            
            summary = f"\n{'='*50}\n"
            summary += f"转换完成！总计: {total} 个文件\n"
            summary += f"✅ 成功: {success} 个\n"
            summary += f"❌ 失败: {failed} 个\n"
            summary += f"{'='*50}\n"
            self.progress_text.insert(tk.END, summary)
            self.progress_text.see(tk.END)
            
            self.current_file_label.config(text="无", fg="gray")
            
            message_type = "完成" if failed == 0 else "部分完成"
            messagebox.showinfo(
                message_type, 
                f"视频转换任务{message_type}！\n\n✅ 成功: {success} 个\n❌ 失败: {failed} 个"
            )
        
        self.root.after(0, _finish)
    
    def on_close(self):
        if self.is_converting and self.current_process:
            if messagebox.askyesno("确认", "转换正在进行中，确定要关闭吗？"):
                if self.current_process:
                    self.current_process.terminate()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoConverterApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
