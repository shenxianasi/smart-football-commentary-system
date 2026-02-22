# 视频分析部分

## 介绍

该部分的目标是使用 YOLO 检测和跟踪视频中的球员、裁判和足球，选择 AI 对象检测模型YOLO ，训练模型以提高其性能。此外，我们将根据球员的 T 恤颜色将球员分配到团队，使用 Kmeans 进行像素分割和聚类。有了这些信息，我们就可以衡量一支球队在比赛中的控球百分比。我们还将使用光流来测量帧之间的摄像机移动，从而能够准确测量玩家的移动。此外，我们将实现透视转换来表示场景的深度和透视，从而允许我们以米而不是像素为单位测量玩家的移动。最后，我们将计算球员的速度和覆盖的距离。该部分从视频中提取到了重要信息，帮助模型更好的生成解说词。
![Screenshot](output_videos/screenshot.jpg)

## 模型
所使用模型如下:
- YOLO: 目标检测模型
- Kmeans: 像素分割和聚类检测t恤颜色
- Optical Flow: 测量摄像头移动
- Perspective Transformation: 透视变换 表示场景深度和视角
- Speed and distance calculation per player

## 训练后的模型
- [Trained Yolo v8](models/1_unchange_better/best.pt)

## Requirements
运行环境:
- Python 3.x
- ultralytics
- supervision
- OpenCV
- NumPy
- Matplotlib
- Pandas