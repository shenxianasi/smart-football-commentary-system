import cv2
import numpy as np
from collections import deque
import time
import os
import glob
import torch
from ultralytics import YOLO

# 设置参数
INPUT_FOLDER = "./input_video"  # 输入视频文件夹
MODULE_PATH = "best.pt"  # 模型路径
BALL_CLASS_ID = 0  # 球的类别ID
CONF_THRESHOLD = 0.3  # 置信度阈值
TRAJECTORY_SECONDS = 1  # 轨迹时间长度(秒)
OUTPUT_FOLDER = "./output_video"  # 输出视频文件夹
DELETE_ORIGINAL = False  # 是否删除原始视频

# 确保输入目录存在
if not os.path.exists(INPUT_FOLDER):
    print(f"输入目录不存在: {INPUT_FOLDER}")
    exit()

# 获取输入目录中的所有视频文件
video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv']
video_files = []
for ext in video_extensions:
    video_files.extend(glob.glob(os.path.join(INPUT_FOLDER, ext)))

if not video_files:
    print(f"在 {INPUT_FOLDER} 中没有找到视频文件")
    exit()

print(f"找到 {len(video_files)} 个视频文件:")
for i, video_file in enumerate(video_files):
    print(f"  {i + 1}. {os.path.basename(video_file)}")

# 确保输出目录存在
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print(f"加载YOLO模型：{MODULE_PATH}")
try:
    # 使用Ultralytics加载模型
    model = YOLO(MODULE_PATH)
    print(f"模型加载成功: {model.names}")
except Exception as e:
    print(f"模型加载失败: {e}")
    print("请检查模型路径是否正确")
    exit()

# 检查CUDA是否可用
cuda_available = torch.cuda.is_available()
print(f"CUDA可用: {'是' if cuda_available else '否'}")
device = "cuda" if cuda_available else "cpu"

# 处理每个视频文件
for video_index, VIDEO_PATH in enumerate(video_files):
    print(f"\n开始处理第 {video_index + 1}/{len(video_files)} 个视频: {os.path.basename(VIDEO_PATH)}")

    # 生成输出文件名
    base_name = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
    OUTPUT_PATH = f"{OUTPUT_FOLDER}/{base_name}_processed2.mp4"

    print("开始处理视频...")
    start_time = time.time()

    # 获取原始视频信息
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"无法打开视频文件: {VIDEO_PATH}")
        continue

    # 获取原始视频参数
    fps = cap.get(cv2.CAP_PROP_FPS)
    orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    print(f"原始视频信息: {orig_width}*{orig_height}, FPS: {fps:.1f}, 总帧数: {total_frames}")

    # 设置视频输出
    out = None
    for codec in ['mp4v', 'avc1', 'XVID', 'MJPG']:
        fourcc = cv2.VideoWriter_fourcc(codec[0], codec[1], codec[2], codec[3])
        out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (orig_width, orig_height))
        if out.isOpened():
            print(f"使用编码器: {codec}")
            break

    if not out or not out.isOpened():
        print("无法初始化视频写入器")
        continue

    # 初始化轨迹
    trajectory_length = int(fps * TRAJECTORY_SECONDS) if fps > 0 else 30
    trajectory = deque(maxlen=trajectory_length)
    print(f"轨迹长度: {trajectory_length}帧 ({TRAJECTORY_SECONDS}秒)")

    # 处理控制
    frame_count = 0
    ball_detected_count = 0

    try:
        # 使用模型预测
        for result in model.predict(
                source=VIDEO_PATH,
                stream=True,
                conf=CONF_THRESHOLD,
                verbose=False,
                device=device,  # 使用检测到的设备
        ):
            frame_count += 1

            # 获取原始尺寸的帧
            orig_frame = result.orig_img.copy()
            output_frame = orig_frame.copy()

            # 处理检测结果 - 只关注球
            ball_position = None
            if result.boxes is not None:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    conf = float(box.conf)

                    if cls_id == BALL_CLASS_ID and conf > CONF_THRESHOLD:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)

                        # 确保坐标在图像范围内
                        cx = max(0, min(cx, orig_width - 1))
                        cy = max(0, min(cy, orig_height - 1))

                        ball_position = (cx, cy)
                        ball_detected_count += 1
                        break

            # 更新轨迹
            if ball_position:
                trajectory.append(ball_position)
            else:
                # 未检测到球时清空轨迹
                trajectory.clear()

            # 只有当检测到球且有轨迹点时才生成特效
            if ball_position and len(trajectory) > 0:
                # 创建轨迹覆盖层
                overlay = np.zeros_like(orig_frame, dtype=np.uint8)

                # 绘制球状拖尾效果
                n = len(trajectory)
                for i, point in enumerate(trajectory):
                    # 计算点在轨迹中的位置比例 (0表示最旧，1表示最新)
                    ratio = i / (n - 1) if n > 1 else 1.0

                    # 计算球的大小
                    min_radius = 2
                    max_radius = 10
                    radius = int(min_radius + (max_radius - min_radius) * ratio)

                    # 计算颜色 (从蓝色到红色渐变)
                    if ratio < 0.5:
                        b = 255
                        g = int(255 * ratio * 2)
                        r = 0
                    else:
                        b = int(255 * (1 - (ratio - 0.5) * 2))
                        g = int(255 * (1 - (ratio - 0.5) * 2))
                        r = int(255 * (ratio - 0.5) * 2)

                    # 在覆盖层上绘制球
                    cv2.circle(overlay, point, radius, (b, g, r), -1)

                # 将覆盖层叠加到原始帧上
                alpha = 0.7
                output_frame = cv2.addWeighted(orig_frame, 1, overlay, alpha, 0)

                # 在最新位置绘制一个较大的实心红点
                cv2.circle(output_frame, ball_position, 8, (0, 0, 255), -1)

            # 确保输出帧尺寸正确
            if output_frame.shape[0] != orig_height or output_frame.shape[1] != orig_width:
                output_frame = cv2.resize(output_frame, (orig_width, orig_height))

            # 写入输出视频
            try:
                out.write(output_frame)
            except Exception as e:
                print(f"写入视频错误: {e}")
                break

            # 进度报告
            if frame_count % 50 == 0 or frame_count == total_frames:
                elapsed_time_so_far = time.time() - start_time
                remaining = (total_frames - frame_count) * (elapsed_time_so_far / frame_count) if frame_count > 0 else 0
                detection_rate = ball_detected_count / frame_count * 100 if frame_count > 0 else 0
                print(f"已处理: {frame_count}/{total_frames} ({frame_count / total_frames * 100:.1f}%) | "
                      f"用时: {elapsed_time_so_far:.1f}s | 剩余: {remaining:.1f}s | "
                      f"检测率: {detection_rate:.1f}%")

    except Exception as e:
        print(f"处理过程中出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 确保资源释放
        if 'out' in locals() and out.isOpened():
            out.release()
            print("视频写入器已释放")

    # 计算处理时间
    elapsed_time = time.time() - start_time
    detection_rate = ball_detected_count / frame_count * 100 if frame_count > 0 else 0

    print(f"\n视频处理完成: {os.path.basename(VIDEO_PATH)}")
    print(f"总帧数: {frame_count}")
    print(f"总用时: {elapsed_time:.2f}秒")
    print(f"平均帧率: {frame_count / max(0.01, elapsed_time):.2f} FPS")
    print(f"球检测率: {ball_detected_count}/{frame_count} ({detection_rate:.1f}%)")
    print(f"输出视频已保存至: {OUTPUT_PATH}")

    # 删除原视频文件
    if DELETE_ORIGINAL:
        try:
            os.remove(VIDEO_PATH)
            print(f"原视频文件已删除: {os.path.basename(VIDEO_PATH)}")
        except Exception as e:
            print(f"删除原视频文件失败: {e}")

print(f"\n所有视频处理完成！共处理了 {len(video_files)} 个视频文件。")