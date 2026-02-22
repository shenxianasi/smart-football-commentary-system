from ultralytics import YOLO
import supervision as sv
import pickle
import os
import numpy as np
import pandas as pd
import cv2
import sys 
sys.path.append('../')
from utils import get_center_of_bbox, get_bbox_width, get_foot_position
from tqdm import tqdm
import datetime

# 添加调试打印函数
def print_debug_info(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG {timestamp}] {message}")

class Tracker:
    def __init__(self, model_path, device='cpu'):
        self.model = YOLO(model_path)
        self.model.to(device)  # 使用to方法设置设备
        self.tracker = sv.ByteTrack()

    def add_position_to_tracks(self,tracks):
        for object, object_tracks in tracks.items():
            for frame_num, track in enumerate(object_tracks):
                for track_id, track_info in track.items():
                    bbox = track_info['bbox']
                    if object == 'ball':
                        position= get_center_of_bbox(bbox)
                    else:
                        position = get_foot_position(bbox)
                    tracks[object][frame_num][track_id]['position'] = position

    def interpolate_ball_positions(self,ball_positions):
        ball_positions = [x.get(1,{}).get('bbox',[]) for x in ball_positions]
        df_ball_positions = pd.DataFrame(ball_positions,columns=['x1','y1','x2','y2'])

        # Interpolate missing values
        df_ball_positions = df_ball_positions.interpolate()
        df_ball_positions = df_ball_positions.bfill()

        ball_positions = [{1: {"bbox":x}} for x in df_ball_positions.to_numpy().tolist()]

        return ball_positions

    def detect_frames(self, frames):
        print_debug_info(f"开始检测 {len(frames)} 帧视频内容")
        batch_size=20
        detections = []
        processed_frames = 0
        
        # 使用tqdm显示检测进度
        with tqdm(total=len(frames), desc="视频帧检测", unit="帧") as pbar:
            for i in range(0,len(frames),batch_size):
                batch_end = min(i + batch_size, len(frames))
                current_batch_size = batch_end - i
                
                # 每处理5个批次打印一次进度信息
                if i % (batch_size * 5) == 0:
                    print_debug_info(f"检测批次 {i//batch_size + 1}, 处理帧范围: {i}-{batch_end-1}")
                
                try:
                    detections_batch = self.model.predict(frames[i:i+batch_size],conf=0.1)
                    detections += detections_batch
                except Exception as e:
                    print_debug_info(f"检测批次 {i//batch_size + 1} 出错: {str(e)}")
                    # 添加空结果以保持帧数一致
                    for _ in range(current_batch_size):
                        detections.append(None)
                
                pbar.update(current_batch_size)
                processed_frames += current_batch_size
        
        print_debug_info(f"完成视频帧检测，成功处理 {len([d for d in detections if d is not None])}/{len(frames)} 帧")
        return detections


    def get_object_tracks(self, frames, read_from_stub=None, stub_path=None): #25.2.24改过 read_from_stub 从False到None
        print_debug_info(f"开始获取目标跟踪信息，帧数: {len(frames)}")
        
        if read_from_stub and stub_path is not None and os.path.exists(stub_path): #检查是否已有缓存文件
            print_debug_info(f"从缓存文件加载跟踪数据: {stub_path}")
            with open(stub_path,'rb') as f:
                tracks = pickle.load(f)
            return tracks

        print_debug_info("开始检测视频帧中的对象")
        detections = self.detect_frames(frames)

        tracks={
            "players":[],
            "referees":[],
            "ball":[]
        }

        # 使用tqdm显示进度
        with tqdm(total=len(detections), desc="处理视频帧跟踪", unit="帧") as pbar:
            for frame_num, detection in enumerate(detections):
                # 每处理10帧打印一次进度信息
                if frame_num % 10 == 0:
                    print_debug_info(f"处理帧 {frame_num}/{len(detections)}")
                    
                cls_names = detection.names
                cls_names_inv = {v:k for k,v in cls_names.items()}

                # Covert to supervision Detection format
                detection_supervision = sv.Detections.from_ultralytics(detection)

                # Convert GoalKeeper to player object
                for object_ind , class_id in enumerate(detection_supervision.class_id):
                    if cls_names[class_id] == "goalkeeper":
                        detection_supervision.class_id[object_ind] = cls_names_inv["player"]

                # Track Objects
                detection_with_tracks = self.tracker.update_with_detections(detection_supervision)

                tracks["players"].append({})
                tracks["referees"].append({})
                tracks["ball"].append({})

                for frame_detection in detection_with_tracks:
                    bbox = frame_detection[0].tolist()
                    cls_id = frame_detection[3]
                    track_id = frame_detection[4]

                    if cls_id == cls_names_inv['player']:
                        tracks["players"][frame_num][track_id] = {"bbox":bbox}
                    
                    if cls_id == cls_names_inv['referee']:
                        tracks["referees"][frame_num][track_id] = {"bbox":bbox}
                
                for frame_detection in detection_supervision:
                    bbox = frame_detection[0].tolist()
                    cls_id = frame_detection[3]

                    if cls_id == cls_names_inv['ball']:
                        tracks["ball"][frame_num][1] = {"bbox":bbox}
                        
                pbar.update(1)

        if stub_path is not None:
            with open(stub_path,'wb') as f:
                pickle.dump(tracks,f)

        return tracks
    
    # def draw_ellipse(self,frame,bbox,color,track_id=None):  #画椭圆
    #     y2 = int(bbox[3])
    #     x_center, _ = get_center_of_bbox(bbox)
    #     width = get_bbox_width(bbox)
    #
    #     cv2.ellipse(
    #         frame,
    #         center=(x_center,y2),
    #         axes=(int(width), int(0.35*width)),
    #         angle=0.0,
    #         startAngle=-45,
    #         endAngle=235,
    #         color = color,
    #         thickness=2,
    #         lineType=cv2.LINE_4
    #     )
    #
    #     #椭圆中心的矩形
    #     rectangle_width = int(0.6*width)
    #     rectangle_height= int(0.4*width)
    #     x1_rect = x_center - rectangle_width//2
    #     x2_rect = x_center + rectangle_width//2
    #     y1_rect = (y2- rectangle_height//2) +15
    #     y2_rect = (y2+ rectangle_height//2) +15
    #
    #     if track_id is not None:
    #         cv2.rectangle(frame,
    #                       (int(x1_rect),int(y1_rect) ),
    #                       (int(x2_rect),int(y2_rect)),
    #                       color,
    #                       cv2.FILLED)
    #
    #         x1_text = x1_rect+12
    #         if track_id > 99:
    #             x1_text -=10
    #
    #         cv2.putText(
    #             frame,
    #             f"{track_id}",
    #             (int(x1_text),int(y1_rect+15)),
    #             cv2.FONT_HERSHEY_SIMPLEX,
    #             2,
    #             (0,0,0),
    #             2
    #         )
    #
    #     return frame

    # 修改2：动态调整矩形和数字大小
    def draw_ellipse(self, frame, bbox, color, track_id=None):
        y2 = int(bbox[3])
        x_center, _ = get_center_of_bbox(bbox)
        width = get_bbox_width(bbox)

        cv2.ellipse(
            frame,
            center=(x_center, y2),
            axes=(int(width), int(0.35 * width)),
            angle=0.0,
            startAngle=-45,
            endAngle=235,
            color=color,
            thickness=2,
            lineType=cv2.LINE_4
        )

        # 椭圆中心的矩形
        rectangle_width = int(0.6 * width)
        rectangle_height = int(0.4 * width)
        x1_rect = x_center - rectangle_width // 2
        x2_rect = x_center + rectangle_width // 2
        y1_rect = (y2 - rectangle_height // 2) + 15
        y2_rect = (y2 + rectangle_height // 2) + 15

        if track_id is not None:
            cv2.rectangle(
                frame,
                (int(x1_rect), int(y1_rect)),
                (int(x2_rect), int(y2_rect)),
                color,
                cv2.FILLED
            )

            # 动态计算字体大小和位置
            text = str(track_id)
            font = cv2.FONT_HERSHEY_SIMPLEX
            initial_scale = 1.0  # 初始字体缩放比例
            thickness = 2  # 初始线条粗细

            # 计算允许的最大文本尺寸（考虑边距）
            margin_x, margin_y = 5, 5
            max_text_width = rectangle_width - 2 * margin_x
            max_text_height = rectangle_height - 2 * margin_y

            # 获取初始文本尺寸
            (text_width, text_height), baseline = cv2.getTextSize(text, font, initial_scale, thickness)
            text_total_height = text_height + baseline  # 包含基线高度的总高度

            # 动态调整缩放比例
            if text_width > max_text_width or text_total_height > max_text_height:
                width_ratio = max_text_width / text_width
                height_ratio = max_text_height / text_total_height
                scale = initial_scale * min(width_ratio, height_ratio)
            else:
                scale = initial_scale

            # 重新计算调整后的文本尺寸
            (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
            text_total_height = text_height + baseline

            # 计算文本位置（居中）
            x_center_rect = x1_rect + rectangle_width // 2
            y_center_rect = y1_rect + rectangle_height // 2
            x_text = x_center_rect - text_width // 2
            y_text = y_center_rect + (text_height - baseline) // 2  # 垂直居中调整

            # 根据缩放比例调整线条粗细
            adjusted_thickness = max(1, int(thickness * scale))

            cv2.putText(
                frame,
                text,
                (int(x_text), int(y_text)),
                font,
                scale,
                (0, 0, 0),
                adjusted_thickness
            )

        return frame

    def draw_traingle(self,frame,bbox,color): #三角形
        y= int(bbox[1])
        x,_ = get_center_of_bbox(bbox)

        triangle_points = np.array([
            [x,y],
            [x-10,y-20],
            [x+10,y-20],
        ])
        cv2.drawContours(frame, [triangle_points],0,color, cv2.FILLED)
        cv2.drawContours(frame, [triangle_points],0,(0,0,0), 2)

        return frame

    def draw_team_ball_control(self,frame,frame_num,team_ball_control):
        # Draw a semi-transparent rectaggle 
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 100), (500,200), (255,255,255), -1 )
        alpha = 0.4
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

        team_ball_control_till_frame = team_ball_control[:frame_num+1]
        # Get the number of time each team had ball control
        team_1_num_frames = team_ball_control_till_frame[team_ball_control_till_frame==1].shape[0]
        team_2_num_frames = team_ball_control_till_frame[team_ball_control_till_frame==2].shape[0]
        
        # 防止除零错误
        total_frames = team_1_num_frames + team_2_num_frames
        if total_frames == 0:
            team_1 = 0.0
            team_2 = 0.0
        else:
            team_1 = team_1_num_frames / total_frames
            team_2 = team_2_num_frames / total_frames

        cv2.putText(frame, f"Team 1 Ball Control: {team_1*100:.2f}%",(10,130), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 3)
        cv2.putText(frame, f"Team 2 Ball Control: {team_2*100:.2f}%",(10,160), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 3)

        return frame

    def draw_annotations(self,video_frames, tracks,team_ball_control): #画圆圈
        output_video_frames= []
        for frame_num, frame in enumerate(video_frames):

            #enumerate用例
            # seasons = ['Spring', 'Summer', 'Fall', 'Winter']
            # >> > list(enumerate(seasons))
            # [(0, 'Spring'), (1, 'Summer'), (2, 'Fall'), (3, 'Winter')]
            # >> > list(enumerate(seasons, start=1))  # 下标从 1 开始
            # [(1, 'Spring'), (2, 'Summer'), (3, 'Fall'), (4, 'Winter')]



            frame = frame.copy()

            player_dict = tracks["players"][frame_num]
            ball_dict = tracks["ball"][frame_num]
            referee_dict = tracks["referees"][frame_num]

            # Draw Players
            for track_id, player in player_dict.items():
                color = player.get("team_color",(0,0,255))
                frame = self.draw_ellipse(frame, player["bbox"],color, track_id)

                if player.get('has_ball',False):
                    frame = self.draw_traingle(frame, player["bbox"],(0,255,0))

            # Draw Referee
            for _, referee in referee_dict.items():
                frame = self.draw_ellipse(frame, referee["bbox"],(0,255,255))
            
            # Draw ball 
            for track_id, ball in ball_dict.items():
                frame = self.draw_traingle(frame, ball["bbox"],(255,255,255))


            # Draw Team Ball Control
            frame = self.draw_team_ball_control(frame, frame_num, team_ball_control)

            output_video_frames.append(frame)

        return output_video_frames