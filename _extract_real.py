import cv2
import os

videos = [
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-29 004120.mp4", "v1", 2.0),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-29 034543.mp4", "v2", 2.0),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 090135.mp4", "v3", 2.0),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 090825.mp4", "v4", 3.0),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 105338.mp4", "v5", 0.5),
    (r"C:\Users\28049\OneDrive\视频\屏幕录制\屏幕录制 2026-08-31 105539.mp4", "v6", 0.5),
]

output_base = r"D:\Taikoo-monitor-new\ref_gpt_v2\real_frames"

total_saved = 0
for video_path, name, interval_sec in videos:
    if not os.path.exists(video_path):
        print(f"❌ {name}: 文件不存在")
        continue
    
    out_dir = os.path.join(output_base, name)
    os.makedirs(out_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    frame_interval = max(1, int(fps * interval_sec))
    
    saved = 0
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % frame_interval == 0:
            ts = idx / fps
            # 缩小宽度到1200以节省空间（保持比例）
            h, w = frame.shape[:2]
            if w > 1200:
                new_w = 1200
                new_h = int(h * new_w / w)
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            fname = f"{name}_{saved:03d}_{ts:.1f}s.jpg"
            cv2.imwrite(os.path.join(out_dir, fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            saved += 1
        idx += 1
    
    cap.release()
    total_saved += saved
    print(f"✅ {name}: {duration:.1f}s, 提取 {saved} 帧 (每{interval_sec}s一帧)")

print(f"\n总计提取: {total_saved} 帧")
print(f"输出目录: {output_base}")
