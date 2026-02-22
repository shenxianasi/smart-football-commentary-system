import cv2

def read_video(video_path):
    # 创建VideoCapture对象cap，用于从指定路径读取视频文件
    cap = cv2.VideoCapture(video_path)
    frames = []
    # 逐帧读取视频
    while True:
        ret , frame = cap.read() 
        # frame 存储为numpy数组，形状为[height,width,channels]
        # ret 是一个bool值，表示视频是否读取成功
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames

def save_video(output_video_frames,output_video_path):
    # 创建FourCC编码器，用于指定视频编解码格式
    fourcc = cv2.VideoWriter_fourcc(*'XVID') # 'XVID'是一种MPEG-4视频编码格式
    # 采用帧率为24，宽高与输入视频相同
    out = cv2.VideoWriter(output_video_path,fourcc,24,(output_video_frames[0].shape[1],output_video_frames[0].shape[0]))
    for frame in output_video_frames:
        out.write(frame)
    out.release()

