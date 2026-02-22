import cv2
import numpy as np
from model import Web_Detector
from offside_detector import OffsideDetector
import os

def test_offside_system():
    """测试越位检测系统"""
    print("开始测试越位检测系统...")
    
    # 加载模型
    print("正在加载球场分割模型...")
    model = Web_Detector()
    model.load_model("./runs/segment/train4/weights/best.pt")
    
    # 初始化越位检测器
    print("正在初始化越位检测器...")
    offside_detector = OffsideDetector()
    
    # 读取视频的第一帧进行测试
    video_path = './input_video/a1.mp4'
    print(f"正在读取视频: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("错误: 无法打开视频文件")
        return
    
    # 测试前5帧
    for frame_num in range(1, 6):
        ret, frame = cap.read()
        if not ret:
            break
            
        print(f"\n=== 测试第 {frame_num} 帧 ===")
        
        # 进行球场分割检测
        pre_img = model.preprocess(frame)
        pred = model.predict(pre_img)
        det = pred[0]
        
        penalty_areas = []
        
        if det is not None and len(det):
            det_info = model.postprocess(pred)
            print(f"检测到 {len(det_info)} 个区域")
            
            # 只保留18码禁区
            for info in det_info:
                if info['class_name'] == '18码禁区':
                    penalty_areas.append(info)
                    print(f"  禁区检测: {info['class_name']}, 置信度: {info['score']:.3f}")
        
        print(f"找到 {len(penalty_areas)} 个禁区区域")
        
        # 进行越位检测
        if penalty_areas:
            processed_frame, offside_info = offside_detector.process_frame(frame, penalty_areas, frame_num)
            
            if offside_info:
                print(f"  ⚠️  检测到越位！队伍{offside_info['offside_team']}")
            else:
                print("  未检测到越位")
            
            # 保存测试结果
            cv2.imwrite(f'./test_offside_frame_{frame_num}.jpg', processed_frame)
            print(f"  保存: test_offside_frame_{frame_num}.jpg")
        else:
            print("  未检测到禁区，跳过越位检测")
    
    cap.release()
    print("\n测试完成")

if __name__ == "__main__":
    test_offside_system() 