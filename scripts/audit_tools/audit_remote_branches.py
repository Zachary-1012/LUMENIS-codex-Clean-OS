import subprocess, os
os.chdir(r"D:\Taikoo-monitor-new")
def git(*args):
    return subprocess.run(["git"]+list(args), capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout

main = "origin/main"
# 所有远程分支，按最后提交时间倒序
branches = [b.strip() for b in git("for-each-ref","--sort=-committerdate","--format=%(refname:short)","refs/remotes/origin").splitlines() if b.strip()]
branches = [b for b in branches if b not in ("origin/HEAD","origin/main")]
print(f"线上分支总数(除main): {len(branches)}")
print(f"{'分支':<55} {'最后提交':<12} {'领先main':>6} {'改动文件':>6}  关键改动")
print("-"*120)
valuable = []
for b in branches:
    date = git("log","-1","--format=%cs",b).strip()
    ahead = git("rev-list","--count",f"{main}..{b}").strip()
    try:
        nahead = int(ahead)
    except: nahead = 0
    if nahead == 0:
        continue  # 已合入main或无新内容
    files = git("diff","--name-only",f"{main}...{b}").splitlines()
    nf = len([f for f in files if f.strip()])
    # 关键改动关键词
    keys = []
    for f in files:
        fl = f.lower()
        for k in ("i18n","locale","podcast","kos","account","totp","auth","runtime","guardian",
                  "collector","risk","report","ui","design","token","icon","skill","agent",
                  "evidence","canonical","scheduler","preflight","keyboard","video","browser",
                  "cookie","wechat","notification","api","permission","security"):
            if k in fl:
                keys.append(k); break
    key_str = ",".join(sorted(set(keys))[:6])
    print(f"{b:<55} {date:<12} {nahead:>6} {nf:>6}  {key_str}")
    valuable.append((b,date,nahead,nf,files,key_str))

print("\n===== 有价值未合分支(领先main>0) =====")
print(f"共 {len(valuable)} 个分支含main没有的commit")
