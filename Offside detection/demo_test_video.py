import random
import cv2
import numpy as np
from hashlib import md5
from model import Web_Detector
from chinese_name_list import Label_list
from offside_detector import OffsideDetector
import os
from PIL import Image, ImageDraw, ImageFont

def generate_color_based_on_name(name):
    # 使用哈希函数生成稳定的颜色
    hash_object = md5(name.encode())
    hex_color = hash_object.hexdigest()[:6]  # 取前6位16进制数
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (b, g, r)  # OpenCV 使用BGR格式

def calculate_polygon_area(points):
    return cv2.contourArea(points.astype(np.float32))


def adjust_parameter(image_size, base_size=1000):
    max_size = max(image_size)
    return max_size / base_size


def draw_detections(image, info, alpha=0.2):
    name, bbox, conf, cls_id, mask = info['class_name'], info['bbox'], info['score'], info['class_id'], info['mask']
    adjust_param = adjust_parameter(image.shape[:2])

    if mask is None:
        x1, y1, x2, y2 = bbox
        aim_frame_area = (x2 - x1) * (y2 - y1)
        cv2.rectangle(image, (x1, y1), (x2, y2), color=(0, 0, 255), thickness=int(3 * adjust_param))
    else:
        mask_points = np.concatenate(mask)
        aim_frame_area = calculate_polygon_area(mask_points)
        mask_color = generate_color_based_on_name(name)
        try:
            overlay = image.copy()
            cv2.fillPoly(overlay, [mask_points.astype(np.int32)], mask_color)
            image = cv2.addWeighted(overlay, 0.3, image, 0.7, 0)
            cv2.drawContours(image, [mask_points.astype(np.int32)], -1, (0, 0, 255), thickness=int(8 * adjust_param))

        except Exception as e:
            print(f"An error occurred: {e}")

    return image, aim_frame_area


def add_chinese_text_to_frame(frame, text, font_size=60, color=(255, 0, 0)):
    """在帧上添加中文字符，支持透明背景"""
    # 将OpenCV图像转换为PIL图像
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)
    
    # 创建透明图层用于文字
    text_layer = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    
    # 尝试加载中文字体，如果失败则使用默认字体
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("simhei.ttf", font_size)  # 黑体
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)  # Arial
        except:
            font = ImageFont.load_default()  # 默认字体
    
    # 获取文字大小
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算文字位置（居中）
    x = (pil_image.width - text_width) // 2
    y = (pil_image.height - text_height) // 2
    
    # 绘制文字（红色）
    draw.text((x, y), text, font=font, fill=(color[0], color[1], color[2], 255))
    
    # 将文字图层合并到原图像
    pil_image = Image.alpha_composite(pil_image.convert('RGBA'), text_layer)
    
    # 转换回OpenCV格式
    frame_rgb = np.array(pil_image.convert('RGB'))
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    
    return frame_bgr


def add_no_offside_marker(video_path, fps, total_frames):
    """在视频末尾2秒添加'未检测到越位'标记"""
    # 计算末尾2秒对应的帧数
    end_frames = int(2 * fps)
    start_frame = max(0, total_frames - end_frames)
    
    # 读取原视频
    cap = cv2.VideoCapture(video_path)
    
    # 创建临时输出文件
    temp_path = video_path.replace('.mp4', '_temp.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, fps, (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), 
                                                   int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
    
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # 在末尾2秒添加标记
        if frame_count >= start_frame:
            # 使用新的函数添加中文文字
            frame = add_chinese_text_to_frame(frame, "未检测到越位", font_size=60, color=(255, 0, 0))
        
        out.write(frame)
        frame_count += 1
    
    cap.release()
    out.release()
    
    # 替换原文件
    os.remove(video_path)
    os.rename(temp_path, video_path)
    print("已在视频末尾添加'未检测到越位'标记")


def process_frame(model, image, offside_detector, frame_count):
    pre_img = model.preprocess(image)
    pred = model.predict(pre_img)
    det = pred[0]

    penalty_areas = []  # 存储禁区信息
    
    if det is not None and len(det):
        det_info = model.postprocess(pred)
        # 只保留18码禁区线的检测
        penalty_area_names = ['18码禁区']
        
        # 添加调试信息
        detected_classes = []
        for info in det_info:
            detected_classes.append(info['class_name'])
            if info['class_name'] in penalty_area_names:
                print(f"检测到禁区线: {info['class_name']}, 置信度: {info['score']:.3f}")
                image, _ = draw_detections(image, info)
                penalty_areas.append(info)  # 保存禁区信息用于越位检测
        
        # 如果检测到任何类别，打印所有检测到的类别
        if detected_classes:
            print(f"当前帧检测到的所有类别: {list(set(detected_classes))}")
    
    # 进行越位检测
    offside_info = None
    if penalty_areas:
        image, offside_info = offside_detector.process_frame(image, penalty_areas, frame_count)
        if offside_info:
            print(f"第{frame_count}帧检测到越位！队伍{offside_info['offside_team']}")
    
    return image, offside_info is not None


if __name__ == "__main__":
    cls_name = Label_list
    model = Web_Detector()
    model.load_model("./runs/segment/train4/weights/best.pt")
    
    # 初始化越位检测器
    offside_detector = OffsideDetector()

    # 视频处理
    video_path = './input_video/a1.mp4'  # 输入视频等路径
    cap = cv2.VideoCapture(video_path)
    
    # 创建输出文件夹
    output_dir = './output_video'
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取原视频参数
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 设置输出视频路径
    output_path = os.path.join(output_dir, 'offside_detection_video.mp4')
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    offside_detected = False  # 标记是否检测到越位
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        processed_frame, is_offside = process_frame(model, frame, offside_detector, frame_count)
        
        # 写入处理后的帧
        out.write(processed_frame)
        
        frame_count += 1
        print(f"处理帧数: {frame_count}")
        
        if is_offside:
            offside_detected = True
    
    # 释放资源
    cap.release()
    out.release()
    
    print(f"越位检测视频处理完成，已保存到: {output_path}")
    
    # 如果没有检测到越位，在视频末尾添加"不存在越位犯规"标记
    if not offside_detected:
        print("未检测到越位，正在添加标记...")
        add_no_offside_marker(output_path, fps, total_frames)
    else:
        print("检测到越位，无需添加标记")
