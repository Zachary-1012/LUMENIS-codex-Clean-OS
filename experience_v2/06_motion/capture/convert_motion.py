import subprocess,os
FF=r"D:/lum-toolchain/ffmpeg/bin/ffmpeg.exe"
B=r"D:/LUMENIS_REBUILD/LUMENIS-codex-Clean-OS/experience_v2/06_motion"
srcdir=os.path.join(B,"capture","webm")
for f in sorted(os.listdir(srcdir)):
    if not f.endswith(".webm"):continue
    n=f[:-5]
    src=os.path.join(srcdir,f)
    red = n.startswith("reduced")
    mp4=os.path.join(B,"reduced-motion" if red else "mp4",n+".mp4")
    gif=os.path.join(B,"reduced-motion" if red else "gif",n+".gif")
    subprocess.run([FF,"-y","-i",src,"-vf","fps=30,format=yuv420p","-c:v","libx264","-crf","20","-movflags","+faststart",mp4],check=True,capture_output=True)
    pal=os.path.join(B,"gif","_pal.png");os.makedirs(os.path.dirname(pal),exist_ok=True)
    subprocess.run([FF,"-y","-i",src,"-vf","fps=12,scale=720:-1:flags=lanczos,palettegen",pal],check=True,capture_output=True)
    subprocess.run([FF,"-y","-i",src,"-i",pal,"-lavfi","fps=12,scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse",gif],check=True,capture_output=True)
    if os.path.exists(pal):os.remove(pal)
    print("converted",n)
print("MOTION CONVERT DONE")
