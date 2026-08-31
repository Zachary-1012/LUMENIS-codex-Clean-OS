import cv2
import os

videos = [
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-29 004120.mp4", "v1_0829_004120"),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-29 034543.mp4", "v2_0829_034543"),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 090135.mp4", "v3_0831_090135"),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 090825.mp4", "v4_0831_090825"),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 105338.mp4", "v5_0831_105338"),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 105539.mp4", "v6_0831_105539"),
]

output_base = r"D:\Taikoo-monitor-new\ref_gpt_v2\real_frames"
os.makedirs(output_base, exist_ok=True)

print("=" * 70)
print("视频信息总览")
print("=" * 70)

for video_path, name in videos:
    if not os.path.exists(video_path):
        print(f"❌ {name}: 文件不存在")
        continue
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ {name}: 无法打开")
        continue
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    size_mb = os.path.getsize(video_path) / (1024*1024)
    
    print(f"\n{name}:")
    print(f"  分辨率: {width}x{height} | 帧率: {fps:.1f}fps | 总帧: {frame_count} | 时长: {duration:.1f}s | 大小: {size_mb:.1f}MB")
    
    cap.release()

print("\n" + "=" * 70)
