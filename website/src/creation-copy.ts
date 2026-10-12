export const creationCopy = {
  "zh-CN": {
    title: "也可以，从自己的创作开始。",
    intro: "带上一个想法、一段文字或自己的素材。方案、视频与播客可以独立创作，也可以接着研究继续做。",
    navigation: "选择创作形式", preview: "创作流程示意", action: "查看进入方式",
    note: "手动编辑是基础；AI 协助取决于当前可用能力。你决定采用哪些建议。",
    items: [
      { id: "document", name: "方案与文稿", title: "把零散的想法，写成完整表达。", description: "整理提纲、改写段落、核对引用，保留每一次修改。", input: "自己的 Brief、文字或资料", output: "可继续修改的文稿与方案", stages: ["提纲", "正文", "引用与修订"], detail: "从结构到段落逐步展开；来源和修改记录随作品保留。" },
      { id: "video", name: "视频剪辑", title: "看见每个镜头，也掌握整条时间线。", description: "素材、预览、时间线和检查器各司其职。镜头、字幕与声音分别调整。", input: "自己的脚本、视频与图片", output: "可编辑工程与视频成片", stages: ["镜头", "字幕", "声音"], detail: "在选中片段上调整，回到完整作品中检查；导出前可预览。" },
      { id: "audio", name: "播客制作", title: "让每一段声音，有合适的位置。", description: "从脚本到录音与音轨，保留剪辑、试听和版本恢复的路径。", input: "自己的脚本、录音与音乐", output: "可编辑工程与播客音频", stages: ["人声", "音乐", "音效"], detail: "单独处理音轨，再一起试听；声音调整与文本修订相互衔接。" },
    ],
    from: "从什么开始", to: "要完成什么",
  },
  en: {
    title: "Or start with something of your own.",
    intro: "Bring an idea, some writing, or your own material. Create a proposal, video, or podcast independently—or carry your research into it.",
    navigation: "Choose a creative format", preview: "Creative workflow illustration", action: "View access options",
    note: "Manual editing comes first. AI assistance depends on available capabilities; you choose which suggestions to use.",
    items: [
      { id: "document", name: "Proposals & writing", title: "Give scattered ideas a clear shape.", description: "Build an outline, revise passages, check citations, and keep each revision.", input: "Your brief, writing, or research material", output: "An editable document or proposal", stages: ["Outline", "Draft", "Citations & revisions"], detail: "Move from structure to individual passages. Keep sources and revisions with the work." },
      { id: "video", name: "Video editing", title: "See the shot. Shape the whole story.", description: "Media, viewer, timeline, and inspector each have a purpose. Adjust shots, captions, and sound separately.", input: "Your script, footage, and images", output: "An editable project and rendered video", stages: ["Shots", "Captions", "Sound"], detail: "Adjust the selected clip, then review it in context. Preview before export." },
      { id: "audio", name: "Podcast production", title: "A place for every voice and sound.", description: "Work from script to recording and tracks, with editing, listening, and version recovery in reach.", input: "Your script, recordings, and music", output: "An editable project and podcast audio", stages: ["Voice", "Music", "Effects"], detail: "Work on individual tracks, then listen together. Keep script revisions connected to sound edits." },
    ],
    from: "Start with", to: "Work toward",
  },
  ko: {
    title: "나만의 창작에서 시작해도 좋습니다.",
    intro: "아이디어, 글, 직접 준비한 자료로 시작하세요. 제안서·영상·팟캐스트를 독립적으로 만들거나 리서치를 창작으로 이어갈 수 있습니다.",
    navigation: "창작 형식 선택", preview: "창작 흐름 예시", action: "이용 방법 보기",
    note: "직접 편집이 기본입니다. AI 지원은 사용 가능한 기능에 따라 제공되며, 제안의 채택은 사용자가 결정합니다.",
    items: [
      { id: "document", name: "제안서와 글쓰기", title: "흩어진 생각을 하나의 글로.", description: "개요를 잡고 문장을 다듬고 인용을 확인하며 수정 내역을 남깁니다.", input: "직접 작성한 브리프, 글 또는 자료", output: "계속 수정할 수 있는 문서와 제안서", stages: ["개요", "본문", "인용과 수정"], detail: "전체 구조에서 문장으로 들어갑니다. 출처와 수정 내역은 작품과 함께 남습니다." },
      { id: "video", name: "영상 편집", title: "한 장면을 보고, 전체 흐름을 만듭니다.", description: "소재, 미리보기, 타임라인과 속성 패널을 구분합니다. 장면·자막·소리를 따로 조정합니다.", input: "직접 준비한 대본, 영상과 이미지", output: "편집 가능한 프로젝트와 완성 영상", stages: ["장면", "자막", "소리"], detail: "선택한 클립을 조정한 뒤 전체 흐름에서 확인합니다. 내보내기 전에 미리 봅니다." },
      { id: "audio", name: "팟캐스트 제작", title: "목소리와 소리마다 알맞은 자리를.", description: "대본에서 녹음과 트랙으로 이어지며, 편집·미리 듣기·버전 복원을 함께 다룹니다.", input: "직접 준비한 대본, 녹음과 음악", output: "편집 가능한 프로젝트와 팟캐스트 음원", stages: ["목소리", "음악", "효과음"], detail: "트랙을 따로 다듬고 함께 듣습니다. 대본 수정과 소리 편집을 연결합니다." },
    ],
    from: "시작 자료", to: "만들 결과",
  },
} as const;
