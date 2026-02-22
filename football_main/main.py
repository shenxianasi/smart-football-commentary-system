import os
import json
import threading
import argparse
import datetime
import time
from tqdm import tqdm
from utils import read_video, save_video
from trackers import Tracker
import cv2
import numpy as np
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
from camera_movement_estimator import CameraMovementEstimator
from view_transformer import ViewTransformer
from speed_and_distance_estimator import SpeedAndDistance_Estimator

# 设置环境变量解决 KMeans 内存泄漏问题
os.environ["OMP_NUM_THREADS"] = "1"

# 获取当前脚本所在目录的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 统一输出目录
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 添加调试打印函数
def print_debug_info(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG {timestamp}] {message}")


def main():
    print_debug_info("开始足球视频分析流程")
    start_time = time.time()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Football video analysis')
    parser.add_argument('--input_video', type=str, default=os.path.join(CURRENT_DIR, 'input_videos', 'a1.mp4'),
                        help='Path to the input video file')
    parser.add_argument('--frame_interval', type=int, default=15,
                        help='Frame interval for processing')
    args = parser.parse_args()
    
    print_debug_info(f"使用视频文件: {args.input_video}")
    print_debug_info(f"帧间隔设置: {args.frame_interval}")
    
    # Read Video
    video_frames = read_video(args.input_video)
    
    # 根据帧间隔参数过滤帧
    if args.frame_interval > 1:
        print_debug_info(f"使用帧间隔 {args.frame_interval} 处理视频")
        # 创建处理帧的索引列表
        processed_frame_indices = list(range(0, len(video_frames), args.frame_interval))
        # 获取要处理的帧
        processed_frames = [video_frames[i] for i in processed_frame_indices]
        print_debug_info(f"从 {len(video_frames)} 帧中选择了 {len(processed_frames)} 帧进行处理")
    else:
        print_debug_info("处理所有视频帧")
        processed_frames = video_frames
        processed_frame_indices = list(range(len(video_frames)))


    # tracker = Tracker('models/1_unchange_better/best.pt')
    # 使用绝对路径加载模型，避免相对路径问题
    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print_debug_info(f"使用设备: {device}")
    
    print_debug_info("初始化跟踪器...")
    tracker = Tracker(model_path=os.path.join(CURRENT_DIR, 'models', '1_unchange_better', 'best.pt'), device=device)
    
    print_debug_info("开始获取对象跟踪信息...")
    tracks = tracker.get_object_tracks(processed_frames,
                                       read_from_stub=False,
                                       stub_path='stubs/track_stubs.pkl')
    
    print_debug_info("添加位置信息到跟踪数据...")
    tracker.add_position_to_tracks(tracks)

    print_debug_info("初始化摄像头移动估计器...")
    camera_movement_estimator = CameraMovementEstimator(video_frames[0])
    
    print_debug_info("计算每帧摄像头移动...")
    camera_movement_per_frame = camera_movement_estimator.get_camera_movement(processed_frames,
                                                                                read_from_stub=False,
                                                                                stub_path='stubs/camera_movement_stub.pkl')
    
    print_debug_info("调整跟踪数据中的位置信息...")
    camera_movement_estimator.add_adjust_positions_to_tracks(tracks,camera_movement_per_frame)


    print_debug_info("初始化视角转换器...")
    view_transformer = ViewTransformer()
    
    print_debug_info("添加转换后的位置信息...")
    view_transformer.add_transformed_position_to_tracks(tracks)

    print_debug_info("插值计算球的位置...")
    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

    print_debug_info("初始化速度和距离估计器...")
    speed_and_distance_estimator = SpeedAndDistance_Estimator()
    
    print_debug_info("计算球员速度和距离...")
    speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

    print_debug_info("初始化队伍分配器...")
    team_assigner = TeamAssigner()
    
    print_debug_info("分配队伍颜色...")
    team_assigner.assign_team_color(video_frames[0], 
                                    tracks['players'][0])
    
    print_debug_info("为每个球员分配队伍...")
    total_frames = len(tracks['players'])
    with tqdm(total=total_frames, desc="分配球员队伍", unit="帧") as pbar:
        for frame_num, player_track in enumerate(tracks['players']):
            # 使用处理过的帧进行队伍分配
            for player_id, track in player_track.items():
                team = team_assigner.get_player_team(processed_frames[frame_num],   
                                                     track['bbox'],
                                                     player_id)
                tracks['players'][frame_num][player_id]['team'] = team 
                tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team]
            pbar.update(1)


    print_debug_info("初始化球员-球分配器...")
    player_assigner =PlayerBallAssigner()
    team_ball_control= []
    
    print_debug_info("为每帧分配控球球员...")
    total_frames = len(tracks['players'])
    with tqdm(total=total_frames, desc="分配控球球员", unit="帧") as pbar:
        for frame_num, player_track in enumerate(tracks['players']):
            ball_bbox = tracks['ball'][frame_num][1]['bbox']
            assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

            if assigned_player != -1:
                tracks['players'][frame_num][assigned_player]['has_ball'] = True
                team_ball_control.append(tracks['players'][frame_num][assigned_player]['team'])
            else:
                if team_ball_control:
                    team_ball_control.append(team_ball_control[-1])
                else:
                    team_ball_control.append(1)  # 默认给team 1
            pbar.update(1)
    team_ball_control= np.array(team_ball_control)


    ## Draw
    print_debug_info("绘制标注信息到视频帧...")
    # 如果使用了帧间隔，需要将处理后的帧信息扩展到所有原始帧
    if args.frame_interval > 1:
        print_debug_info(f"将处理结果从 {len(tracks['players'])} 帧扩展到 {len(video_frames)} 帧")
        
        # 创建扩展后的跟踪数据结构
        extended_tracks = {
            "players": [{} for _ in range(len(video_frames))],
            "referees": [{} for _ in range(len(video_frames))],
            "ball": [{} for _ in range(len(video_frames))]
        }
        
        # 扩展后的队伍控球信息
        extended_team_ball_control = np.zeros(len(video_frames), dtype=int)
        
        # 复制处理过的帧的数据到扩展后的数据结构
        for i, frame_idx in enumerate(processed_frame_indices):
            extended_tracks['players'][frame_idx] = tracks['players'][i]
            extended_tracks['referees'][frame_idx] = tracks['referees'][i]
            extended_tracks['ball'][frame_idx] = tracks['ball'][i]
            extended_team_ball_control[frame_idx] = team_ball_control[i]
        
        # 对未处理的帧进行插值填充
        print_debug_info("对未处理的帧进行插值填充...")
        for i in range(1, len(video_frames) - 1):
            if i not in processed_frame_indices:
                # 找到前一个和后一个处理过的帧的索引
                prev_processed = max([j for j in processed_frame_indices if j < i], default=0)
                next_processed = min([j for j in processed_frame_indices if j > i], default=len(video_frames) - 1)
                
                # 简单复制前一处理帧的数据
                extended_tracks['players'][i] = extended_tracks['players'][prev_processed].copy()
                extended_tracks['referees'][i] = extended_tracks['referees'][prev_processed].copy()
                extended_tracks['ball'][i] = extended_tracks['ball'][prev_processed].copy()
                extended_team_ball_control[i] = extended_team_ball_control[prev_processed]
        
        # 使用扩展后的数据绘制标注
        output_video_frames = tracker.draw_annotations(video_frames, extended_tracks, extended_team_ball_control)
    else:
        # 直接使用所有帧进行绘制
        output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)

    print_debug_info("绘制摄像头移动轨迹...")
    # 如果使用了帧间隔，需要扩展摄像头移动数据
    if args.frame_interval > 1:
        extended_camera_movement = [None] * len(video_frames)
        for i, frame_idx in enumerate(processed_frame_indices):
            extended_camera_movement[frame_idx] = camera_movement_per_frame[i]
        # 对未处理的帧进行简单填充
        for i in range(len(video_frames)):
            if extended_camera_movement[i] is None:
                # 找到前一个有数据的帧
                j = i - 1
                while j >= 0 and extended_camera_movement[j] is None:
                    j -= 1
                if j >= 0:
                    extended_camera_movement[i] = extended_camera_movement[j]
                else:
                    extended_camera_movement[i] = (0, 0)  # 默认值
        output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, extended_camera_movement)
    else:
        output_video_frames = camera_movement_estimator.draw_camera_movement(output_video_frames, camera_movement_per_frame)

    print_debug_info("绘制球员速度和距离...")
    if args.frame_interval > 1:
        speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, extended_tracks)
    else:
        speed_and_distance_estimator.draw_speed_and_distance(output_video_frames, tracks)

    # 创建统一的视频输出目录
    video_output_dir = os.path.join(OUTPUT_DIR, "processed_videos")
    os.makedirs(video_output_dir, exist_ok=True)
    
    # 保存视频到统一目录
    output_filename = "video_a1_1.avi"
    output_path = os.path.join(video_output_dir, output_filename)
    print_debug_info(f"保存处理后的视频到统一目录: {output_path}")
    save_video(output_video_frames, output_path)
    
    # 同时保存一份到原位置以保持兼容性
    legacy_output_dir = os.path.join(CURRENT_DIR, "output_videos")
    os.makedirs(legacy_output_dir, exist_ok=True)
    legacy_output_path = os.path.join(legacy_output_dir, output_filename)
    save_video(output_video_frames, legacy_output_path)
    
    # 生成比赛分析数据
    def generate_match_analysis():
        """生成比赛分析数据"""
        analysis = {
            "video_filename": output_filename,
            "total_frames": len(video_frames),
            "processed_frames": len(processed_frames),
            "processing_time": elapsed_time,
            "team_ball_control": team_ball_control.tolist(),
            "has_players": len(tracks["players"]) > 0 if args.frame_interval == 1 else len(extended_tracks["players"]) > 0
        }
        
        # 统计各队控球时间
        if 'team_ball_control' in analysis:
            team1_count = analysis['team_ball_control'].count(1)
            team2_count = analysis['team_ball_control'].count(2)
            analysis['team_stats'] = {
                "team1_control_percentage": (team1_count / len(analysis['team_ball_control'])) * 100 if analysis['team_ball_control'] else 0,
                "team2_control_percentage": (team2_count / len(analysis['team_ball_control'])) * 100 if analysis['team_ball_control'] else 0
            }
        
        return analysis
    
    # 计算总耗时
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # 生成并保存分析数据
    match_analysis = generate_match_analysis()
    analysis_path = os.path.join(CURRENT_DIR, "match_analysis.json")
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump(match_analysis, f, ensure_ascii=False, indent=2)
    print_debug_info(f"比赛分析数据已保存: {analysis_path}")
    
    # 同时保存到统一的analysis目录
    analysis_dir = os.path.join(OUTPUT_DIR, "analysis")
    os.makedirs(analysis_dir, exist_ok=True)
    unified_analysis_path = os.path.join(analysis_dir, f"{os.path.splitext(output_filename)[0]}_analysis.json")
    with open(unified_analysis_path, 'w', encoding='utf-8') as f:
        json.dump(match_analysis, f, ensure_ascii=False, indent=2)
    print_debug_info(f"比赛分析数据已保存到统一目录: {unified_analysis_path}")
    
    print_debug_info(f"足球视频分析流程完成! 总耗时: {elapsed_time:.2f} 秒")

if __name__ == '__main__':
    main()