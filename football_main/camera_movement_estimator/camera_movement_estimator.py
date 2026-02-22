import pickle
import cv2
import numpy as np
import os
import sys 
sys.path.append('../')
from utils import measure_distance,measure_xy_distance

class CameraMovementEstimator():
    def __init__(self,frame):
        self.minimum_distance = 5 #最小移动阈值
        # Lucas-Kanade光流法参数
        self.lk_params = dict(
            winSize = (15,15),  #搜索窗口大小
            maxLevel = 2,       #金字塔层数
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,10,0.03)
        )
        # 创建特征点检测掩码（只检测两侧区域）
        first_frame_grayscale = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        mask_features = np.zeros_like(first_frame_grayscale)
        mask_features[:,0:20] = 1       # 左侧区域
        mask_features[:,900:1050] = 1   # 右侧区域
        # 特征点检测参数
        self.features = dict(
            maxCorners = 100,  # 最大特征点数
            qualityLevel = 0.3,  # 特征点质量阈值
            minDistance = 3,  # 特征点间最小距离
            blockSize = 7,  # 计算窗口大小
            mask = mask_features  # 应用区域掩码
        )
    # 相机运动补偿
    def add_adjust_positions_to_tracks(self,tracks, camera_movement_per_frame):
        for object, object_tracks in tracks.items():
            for frame_num, track in enumerate(object_tracks):
                for track_id, track_info in track.items():
                    position = track_info['position']
                    # 获取当前帧的相机运动
                    camera_movement = camera_movement_per_frame[frame_num]
                    # 计算补偿后的位置
                    position_adjusted = (position[0]-camera_movement[0],position[1]-camera_movement[1])
                    tracks[object][frame_num][track_id]['position_adjusted'] = position_adjusted
                    


    def get_camera_movement(self,frames,read_from_stub=False, stub_path=None):
        # 缓存
        if read_from_stub and stub_path is not None and os.path.exists(stub_path):
            with open(stub_path,'rb') as f:
                return pickle.load(f)

        camera_movement = [[0,0]]*len(frames)  # 初始化运动向量
        # 处理第一帧
        old_gray = cv2.cvtColor(frames[0],cv2.COLOR_BGR2GRAY)
        old_features = cv2.goodFeaturesToTrack(old_gray,**self.features)

        for frame_num in range(1,len(frames)):
            frame_gray = cv2.cvtColor(frames[frame_num],cv2.COLOR_BGR2GRAY)
            # 计算光流
            new_features, _,_ = cv2.calcOpticalFlowPyrLK(old_gray,frame_gray,old_features,None,**self.lk_params)

            max_distance = 0
            camera_movement_x, camera_movement_y = 0,0
            # 寻找最大移动的特征点
            for i, (new,old) in enumerate(zip(new_features,old_features)):
                new_features_point = new.ravel()
                old_features_point = old.ravel()

                distance = measure_distance(new_features_point,old_features_point)
                if distance>max_distance:
                    max_distance = distance
                    # 计算XY方向位移
                    camera_movement_x,camera_movement_y = measure_xy_distance(old_features_point, new_features_point )
            # 超过阈值则记录为相机运动
            if max_distance > self.minimum_distance:
                camera_movement[frame_num] = [camera_movement_x,camera_movement_y]
                # 更新特征点（重检测）
                old_features = cv2.goodFeaturesToTrack(frame_gray,**self.features)

            old_gray = frame_gray.copy()
        
        if stub_path is not None:
            with open(stub_path,'wb') as f:
                pickle.dump(camera_movement,f)

        return camera_movement
    
    def draw_camera_movement(self,frames, camera_movement_per_frame):
        output_frames=[]

        for frame_num, frame in enumerate(frames):
            import cv2

            frame= frame.copy()
            # 半透明背景
            overlay = frame.copy()
            cv2.rectangle(overlay,(0,0),(500,100),(255,255,255),-1)
            alpha =0.6
            cv2.addWeighted(overlay,alpha,frame,1-alpha,0,frame)
            # 运动信息文本
            x_movement, y_movement = camera_movement_per_frame[frame_num]
            frame = cv2.putText(frame,f"Camera Movement X: {x_movement:.2f}",(10,30), cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),3)
            frame = cv2.putText(frame,f"Camera Movement Y: {y_movement:.2f}",(10,60), cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),3)

            output_frames.append(frame) 

        return output_frames