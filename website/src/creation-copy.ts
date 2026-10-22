export const creationCopy = {
  "zh-CN": {
    title: "从自己的想法和素材开始创作。",
    intro: "提案、视频与播客都可以独立开始。你可以带来自己的 Brief、文字或素材；把 CTH / BMP 研究接进创作，是可选的后续联动。",
    navigation: "选择创作形式", start: "开始材料", result: "作品结果",
    note: "保存后的作品可以继续修改、重新打开和导出。采用外部事实或资料时，仍按来源与权限规则处理。",
    items: [
      { id: "document", name: "提案与文稿", title: "把零散想法整理成可继续修改的文稿。", description: "从自己的 Brief、文字或资料开始，逐步写出提纲、正文和提案。", input: "自己的 Brief、文字或资料", output: "可修订的文稿或提案", stages: ["提纲", "正文", "引用与修订"], detail: "作品可以独立完成；如需使用外部资料，来源和使用权限仍需核实。" },
      { id: "video", name: "视频制作", title: "从脚本和素材开始，完成一条可编辑的时间线。", description: "导入自己的脚本、视频和图片，安排镜头、字幕与声音，再预览和导出。", input: "自己的脚本、视频与图片", output: "可编辑的视频工程与成片", stages: ["镜头", "字幕", "声音"], detail: "视频工作可独立于 CTH / BMP 开始；领域研究只在你需要时接入。" },
      { id: "audio", name: "播客制作", title: "把脚本、录音与声音素材组织成播客。", description: "围绕内容、语音和音轨编辑，试听整体效果，并保留可继续修改的工程。", input: "自己的脚本、录音与音乐", output: "可编辑的播客工程与音频", stages: ["脚本", "人声", "音乐与音效"], detail: "播客制作可以独立开始；后续也可选择引用研究或提案中的资料。" },
    ],
  },
  en: {
    title: "Create from your own ideas and material.",
    intro: "Proposals, video, and podcasts can each start on their own. Bring a brief, writing, or your own assets; connecting CTH or BMP research is an optional next step.",
    navigation: "Choose a format", start: "Start with", result: "Create",
    note: "Saved work can be revised, reopened, and exported. Referenced external facts and materials still follow source and permission checks.",
    items: [
      { id: "document", name: "Proposals & writing", title: "Shape scattered ideas into writing you can keep revising.", description: "Start with your brief, writing, or material; build an outline, draft, and proposal step by step.", input: "Your brief, writing, or material", output: "A revisable document or proposal", stages: ["Outline", "Draft", "Citations & revisions"], detail: "Create independently. When you use external material, its source and permitted use still need to be checked." },
      { id: "video", name: "Video production", title: "Turn a script and assets into an editable timeline.", description: "Bring your script, footage, and images; arrange shots, captions, and sound, then preview and export.", input: "Your script, footage, and images", output: "An editable video project and rendered video", stages: ["Shots", "Captions", "Sound"], detail: "Video work can start independently of CTH or BMP. Connect domain research only when you choose." },
      { id: "audio", name: "Podcast production", title: "Bring a script, recordings, and sound together.", description: "Edit the script, voice, and tracks; listen to the whole piece and keep an editable project.", input: "Your script, recordings, and music", output: "An editable podcast project and audio", stages: ["Script", "Voice", "Music & effects"], detail: "Podcast work can start independently and may optionally draw on research or a proposal later." },
    ],
  },
  ko: {
    title: "아이디어와 자료만으로 창작을 시작하세요.",
    intro: "제안서·영상·팟캐스트는 각각 독립적으로 시작할 수 있습니다. 직접 준비한 브리프, 글 또는 자료를 가져오세요. CTH / BMP 리서치 연결은 선택 사항입니다.",
    navigation: "창작 형식 선택", start: "시작 자료", result: "만들 결과",
    note: "저장한 작품은 수정하고 다시 열거나 내보낼 수 있습니다. 외부 사실이나 자료를 인용할 때는 출처와 권한을 확인합니다.",
    items: [
      { id: "document", name: "제안서와 글쓰기", title: "흩어진 생각을 계속 다듬을 수 있는 글로 만듭니다.", description: "직접 작성한 브리프, 글 또는 자료에서 시작해 개요와 본문, 제안서를 차근차근 작성합니다.", input: "직접 작성한 브리프, 글 또는 자료", output: "수정 가능한 문서 또는 제안서", stages: ["개요", "본문", "인용과 수정"], detail: "독립적으로 완성할 수 있습니다. 외부 자료를 사용하면 출처와 사용 권한을 확인합니다." },
      { id: "video", name: "영상 제작", title: "대본과 자료를 편집 가능한 타임라인으로 만듭니다.", description: "대본, 영상, 이미지를 가져와 장면·자막·소리를 배치하고 미리 본 뒤 내보냅니다.", input: "직접 준비한 대본, 영상과 이미지", output: "편집 가능한 영상 프로젝트와 완성 영상", stages: ["장면", "자막", "소리"], detail: "CTH / BMP와 별개로 시작할 수 있으며, 필요할 때만 영역별 리서치를 연결합니다." },
      { id: "audio", name: "팟캐스트 제작", title: "대본, 녹음과 소리를 하나의 작품으로 엮습니다.", description: "대본과 음성, 트랙을 편집하고 전체를 들어 보며 계속 수정할 수 있는 프로젝트를 남깁니다.", input: "직접 준비한 대본, 녹음과 음악", output: "편집 가능한 팟캐스트 프로젝트와 음원", stages: ["대본", "목소리", "음악과 효과음"], detail: "독립적으로 시작할 수 있고, 이후 리서치나 제안서 자료를 선택해 연결할 수 있습니다." },
    ],
  },
} as const;
