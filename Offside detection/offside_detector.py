import cv2
import numpy as np
from ultralytics import YOLO
from team_assigner import TeamAssigner
from utils.bbox_utils import get_center_of_bbox, get_foot_postion, measure_distance
import os

class OffsideDetector:
    def __init__(self):
        # 加载足球检测模型
        self.ball_model = YOLO('./weights/yolov8n.pt')  # 使用通用检测模型检测足球
        
        # 加载球员检测模型
        self.player_model = YOLO('./weights/yolov8n.pt')  # 使用通用检测模型检测球员
        
        # 初始化队伍分配器
        self.team_assigner = TeamAssigner()
        
        # 越位检测参数
        self.offside_threshold = 50  # 越位判定阈值（像素）
        self.last_offside_frame = 0  # 上次检测到越位的帧数
        self.offside_cooldown = 30   # 越位检测冷却帧数
        
    def detect_ball(self, frame):
        """检测足球位置"""
        results = self.ball_model(frame, classes=[32])  # class 32 是足球
        ball_detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    bbox = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    if conf > 0.3:  # 置信度阈值
                        ball_detections.append({
                            'bbox': bbox,
                            'confidence': conf,
                            'center': get_center_of_bbox(bbox)
                        })
        
        return ball_detections
    
    def detect_players(self, frame):
        """检测球员位置"""
        results = self.player_model(frame, classes=[0])  # class 0 是人
        player_detections = {}
        
        for i, result in enumerate(results):
            boxes = result.boxes
            if boxes is not None:
                for j, box in enumerate(boxes):
                    bbox = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    if conf > 0.5:  # 置信度阈值
                        player_id = i * 100 + j
                        player_detections[player_id] = {
                            'bbox': bbox,
                            'confidence': conf,
                            'center': get_center_of_bbox(bbox),
                            'foot_position': get_foot_postion(bbox)
                        }
        
        return player_detections
    
    def is_ball_in_penalty_area(self, ball_center, penalty_areas):
        """判断足球是否在大禁区内"""
        if not penalty_areas:
            return False
            
        for area in penalty_areas:
            if area['class_name'] == '18码禁区':
                mask_points = np.concatenate(area['mask'])
                # 检查球心是否在禁区内
                if cv2.pointPolygonTest(mask_points.astype(np.float32), 
                                      (ball_center[0], ball_center[1]), False) >= 0:
                    return True
        return False
    
    def get_players_in_penalty_area(self, players, penalty_areas):
        """获取在大禁区内的球员"""
        players_in_area = {}
        
        for area in penalty_areas:
            if area['class_name'] == '18码禁区':
                mask_points = np.concatenate(area['mask'])
                
                for player_id, player in players.items():
                    foot_pos = player['foot_position']
                    # 检查球员脚部位置是否在禁区内
                    if cv2.pointPolygonTest(mask_points.astype(np.float32), 
                                          (foot_pos[0], foot_pos[1]), False) >= 0:
                        players_in_area[player_id] = player
        
        return players_in_area
    
    def check_offside(self, players_in_area, frame_count, frame):
        """检查越位"""
        if not players_in_area or len(players_in_area) < 2:
            return None
            
        # 避免频繁检测越位
        if frame_count - self.last_offside_frame < self.offside_cooldown:
            return None
            
        # 分配队伍
        self.team_assigner.assign_team_color(frame, players_in_area)
        
        # 按x坐标排序球员（从左到右）
        sorted_players = sorted(players_in_area.items(), 
                              key=lambda x: x[1]['center'][0])
        
        # 检查是否有越位
        for i, (player_id, player) in enumerate(sorted_players):
            team_id = self.team_assigner.get_player_team(frame, player['bbox'], player_id)
            
            # 检查该球员是否是最右边的进攻球员
            if i == len(sorted_players) - 1:  # 最右边的球员
                # 检查是否有防守球员在更右边
                for j, (other_id, other_player) in enumerate(sorted_players[:-1]):
                    other_team_id = self.team_assigner.get_player_team(frame, other_player['bbox'], other_id)
                    
                    if other_team_id != team_id:  # 不同队伍
                        # 计算距离
                        distance = abs(player['center'][0] - other_player['center'][0])
                        
                        if distance < self.offside_threshold:
                            self.last_offside_frame = frame_count
                            return {
                                'offside_player_id': player_id,
                                'offside_team': team_id,
                                'position': player['center']
                            }
        
        return None
    
    def draw_offside_warning(self, frame, offside_info):
        """在视频上绘制越位警告"""
        if offside_info:
            pos = offside_info['position']
            team = offside_info['offside_team']
            
            # 绘制越位文字
            text = f"越位 - 队伍{team}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 2.0
            thickness = 3
            color = (0, 0, 255)  # 红色
            
            # 获取文字大小
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            
            # 绘制背景矩形
            cv2.rectangle(frame, 
                         (pos[0] - text_width//2 - 10, pos[1] - text_height - 10),
                         (pos[0] + text_width//2 + 10, pos[1] + baseline + 10),
                         (255, 255, 255), -1)
            
            # 绘制文字
            cv2.putText(frame, text, 
                       (pos[0] - text_width//2, pos[1]), 
                       font, font_scale, color, thickness)
            
            # 绘制圆圈标记越位球员
            cv2.circle(frame, pos, 20, color, 3)
    
    def process_frame(self, frame, penalty_areas, frame_count):
        """处理单帧，进行越位检测"""
        # 检测足球
        ball_detections = self.detect_ball(frame)
        
        # 检测球员
        player_detections = self.detect_players(frame)
        
        offside_info = None
        
        if ball_detections:
            ball_center = ball_detections[0]['center']
            
            # 检查足球是否在大禁区内
            if self.is_ball_in_penalty_area(ball_center, penalty_areas):
                # 获取禁区内的球员
                players_in_area = self.get_players_in_penalty_area(player_detections, penalty_areas)
                
                # 检查越位
                offside_info = self.check_offside(players_in_area, frame_count, frame)
        
        # 绘制越位警告
        self.draw_offside_warning(frame, offside_info)
        
        return frame, offside_info 