import cv2
import os
from tqdm import tqdm
import datetime

# 添加调试打印函数
def print_debug_info(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG {timestamp}] {message}")

def read_video(video_path):
    print_debug_info(f"开始读取视频文件: {video_path}")
    
    # 检查文件是否存在
    if not os.path.exists(video_path):
        print_debug_info(f"错误：视频文件不存在: {video_path}")
        return []
        
    cap = cv2.VideoCapture(video_path)
    
    # 获取视频信息
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print_debug_info(f"视频信息 - 帧数: {frame_count}, FPS: {fps:.2f}, 分辨率: {width}x{height}")
    
    frames = []
    # 使用tqdm显示进度
    with tqdm(total=frame_count, desc="读取视频帧", unit="帧") as pbar:
        # 逐帧读取视频
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            pbar.update(1)
    
    cap.release()
    print_debug_info(f"视频读取完成，共读取 {len(frames)} 帧")
    return frames

def save_video(ouput_video_frames,output_video_path):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_video_path, fourcc, 24, (ouput_video_frames[0].shape[1], ouput_video_frames[0].shape[0]))
    for frame in ouput_video_frames:
        out.write(frame)
    out.release()
