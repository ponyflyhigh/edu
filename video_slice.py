from moviepy import VideoFileClip
import os

def split_video_and_audio(input_video_path, output_dir, clip_duration):
    # 加载视频文件
    video = VideoFileClip(input_video_path)
    audio = video.audio  # 获取视频中的音频

    # 获取视频的总时长（秒）
    total_duration = video.duration
    
    # 获取视频文件名，不带路径和扩展名
    base_filename = os.path.splitext(os.path.basename(input_video_path))[0]

    # 计算切割的片段数
    num_clips = int(total_duration // clip_duration)

    # 提取完整音频，只提取一次
    audio_output_path = os.path.join(output_dir, base_filename, f"{base_filename}_full_audio.mp3")
    os.makedirs(os.path.join(output_dir, base_filename), exist_ok=True)
    audio.write_audiofile(audio_output_path, codec="libmp3lame")

    # 视频按时长切割成多个片段
    for i in range(num_clips):
        start_time = i * clip_duration
        end_time = start_time + clip_duration

        # 截取视频片段
        video_clip = video.subclipped(start_time, end_time)

        # 创建输出文件夹
        clip_output_dir = os.path.join(output_dir, base_filename)
        os.makedirs(clip_output_dir, exist_ok=True)

        # 保存视频片段
        video_output_path = os.path.join(clip_output_dir, f"{base_filename}_clip_{i+1}.mp4")
        video_clip.write_videofile(video_output_path, codec="libx264", audio_codec="aac")

    # 如果视频剩余部分小于 clip_duration，也保存它
    remaining_time = total_duration % clip_duration
    if remaining_time > 0:
        video_clip = video.subclipped(num_clips * clip_duration, total_duration)

        # 创建输出文件夹
        clip_output_dir = os.path.join(output_dir, base_filename)
        os.makedirs(clip_output_dir, exist_ok=True)

        # 保存剩余的视频片段
        video_output_path = os.path.join(clip_output_dir, f"{base_filename}_clip_{num_clips+1}.mp4")
        video_clip.write_videofile(video_output_path, codec="libx264", audio_codec="aac")

# 使用示例
input_video = r"C:\Users\86132\Desktop\education\data\video\file1.mp4"  # 输入视频路径
output_directory = "output"  # 输出文件夹路径
clip_length = 300  # 每个片段的时长，单位为秒

split_video_and_audio(input_video, output_directory, clip_length)
