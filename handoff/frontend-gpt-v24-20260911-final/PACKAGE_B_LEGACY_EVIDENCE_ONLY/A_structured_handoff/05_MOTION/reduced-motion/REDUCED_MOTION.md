# Reduced-Motion 策略（真实实现）
- 所有截图 / QA 探针在 `prefers-reduced-motion: reduce` 下采集：动效退化为瞬时透明度/终态，不做位移与持续流光。
- M01–M15 每条均在 MOTION_REGISTRY.json 带 `reduced_motion` 降级描述。
- motion.js 运行时读取 matchMedia('(prefers-reduced-motion: reduce)')；orb.js 在 reduce 下只渲染单帧、不跑 rAF 循环。
- 演示视频 experience-overview.mp4/.gif 保留正常动效以展示设计意图；04_VISUAL_BASELINES 全部为 reduce 终态基线。
