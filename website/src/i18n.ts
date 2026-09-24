export const locales = ["zh-CN", "en", "ko"] as const;
export type Locale = (typeof locales)[number];

export const copy = {
  "zh-CN": {
    lang: "zh-CN",
    languageName: "简体中文",
    productName: "序境 LUMENIS",
    metadata: {
      title: "序境 LUMENIS｜让每条线索都能回到来处",
      description:
        "认识序境 LUMENIS：面向商业运营与品牌市场工作，连接有来源的资料、业务判断、内容计划与复盘。",
    },
    navigation: [
      { href: "#structure", label: "产品结构" },
      { href: "#scenarios", label: "使用情境" },
      { href: "#demo", label: "示意体验" },
      { href: "#access", label: "访问方式" },
    ],
    languageNavigationLabel: "选择语言",
    primaryNavigationLabel: "产品介绍导航",
    headerNote: "产品探索",
    skipLabel: "跳到主要内容",
    hero: {
      eyebrow: "一条线索，不止一个终点",
      title: "沿着变化，看见来处与去向。",
      description:
        "面向商业运营与品牌市场团队，把有来源的资料、待核实的问题、业务判断和交付物放在同一条工作脉络里。",
      primary: "看一段示意线索",
      secondary: "了解产品结构",
      note: "本页是产品介绍；示意内容为虚构，不连接真实产品数据。",
      diagramLabel: "从资料整理到业务交付，再根据反馈复盘下一步。",
      flowLabels: { material: "资料", delivery: "交付", feedback: "反馈" },
    },
    sequence: {
      heading: "从资料走到交付，再复盘结果",
      intro: "每一步都围绕可核对的资料、明确的问题、业务判断与实际反馈展开。",
      returnLabel: "根据交付后的反馈，修正下一轮计划。",
      nodes: [
        { name: "资料", english: "MATERIAL", meaning: "保留来源、时点与上下文" },
        { name: "问题", english: "QUESTION", meaning: "整理需要核实的事项" },
        { name: "判断", english: "DECISION", meaning: "核对依据后选择下一步" },
        { name: "计划", english: "PLAN", meaning: "明确要完成的工作" },
        { name: "交付", english: "DELIVERY", meaning: "形成团队可以使用的结果" },
        { name: "复盘", english: "REVIEW", meaning: "结合反馈调整后续工作" },
      ],
    },
    structure: {
      eyebrow: "一体产品，四种职责",
      title: "先看问题从哪里开始。",
      intro: "同一产品核心，保留不同领域各自的观察入口；创作与系统基础提供共同支撑。",
      commerce: {
        ordinal: "01 / 商业运营",
        title: "从主体与时间开始",
        description:
          "围绕项目、门店、活动与顾客反馈，核对真实资源和变化，形成有依据的运营判断与待办事项。",
        lens: "主体 → 时间 → 因果线索",
      },
      brand: {
        ordinal: "02 / 品牌与市场",
        title: "从品牌与关系开始",
        description:
          "对照消费者需求、竞品和渠道变化，梳理品牌表达、内容方向与合作选择所需的依据。",
        lens: "品牌 → 关系 → 传播脉络",
      },
      shared: {
        ordinal: "03 / 共享能力",
        title: "创作、研究与评估，共同生长",
        description:
          "让研究发现进入 Brief、内容、报告与评估，保留来源、待确认事项和实际反馈。",
      },
      system: {
        ordinal: "04 / 系统基础",
        title: "让底层职责各归其位",
        description:
          "采集、运行、调度、安全与恢复构成基础；它们支撑产品，不替代业务本身。",
      },
    },
    scenarios: {
      eyebrow: "从真实问题出发",
      title: "让下一步有来由。",
      intro: "以下是适合序境观察方式的典型问题，不是客户案例或效果承诺。",
      commerce: {
        title: "从场内资源到内容计划",
        question: "下个月哪些资源值得采编，哪些还需要门店确认？",
        description:
          "核对项目目录、品牌动态与现场资料，区分已证实的资源和待确认信息，再为内容计划留下依据。",
        path: ["项目任务", "核对资源", "形成计划", "保留依据"],
      },
      brand: {
        title: "从市场研究到品牌 Brief",
        question: "新系列该向谁表达，选择什么内容与合作对象？",
        description:
          "对照消费者情境、竞品、渠道与创作者资料，把有依据的选择和未知项带入 Brief。",
        path: ["品牌任务", "比较依据", "内容选择", "待核实项"],
      },
    },
    demo: {
      eyebrow: "可检查的产品示意",
      title: "从来源到行动，每一步都能回看。",
      intro:
        "拖动时间线，或用键盘方向键逐步查看序境的业务链。这里是明确标注的虚构结构示意：没有实时数据、真实客户记录或已执行操作。",
      illustrativeLabel: "虚构示例 · 非实时数据",
      sourceLabel: "起点 / 虚构来源",
      changeLabel: "变化 / 时间轴",
      traceLabel: "关联 / 线索",
      returnLabel: "返回 / 来源脉络",
      commerce: {
        title: "主体与时间：一次计划调整",
        source: "示意记录：某项计划的预计周期出现调整。",
        change: "把调整放入前后时间脉络，不推断原因。",
        trace: "连接待核对的相关线索，保留问题而非生成结论。",
        back: "回到这条虚构计划记录",
        sourceId: "example-source-commerce",
      },
      brand: {
        title: "品牌与关系：一个议题的传播",
        source: "示意记录：一个品牌议题出现在某个市场语境中。",
        change: "观察它与其他语境之间可能存在的关系。",
        trace: "沿关系展开线索；此示例不代表真实监测或传播结果。",
        back: "回到这条虚构议题记录",
        sourceId: "example-source-brand",
      },
      returnNote: "回到来源，继续检查关联与依据。",
      contextLabel: "示意场景 / 商业运营",
      timelineLabel: "业务链时间线",
      timelineHeading: "从资料，走到结果",
      scrubberLabel: "选择业务链节点",
      scrubberHelp: "拖动滑块，或使用左右方向键逐步浏览。",
      focusLabel: "当前节点",
      viewModeLabel: "示意区排列方式",
      linearView: "线性时间线",
      orbitView: "环形探索",
      returnAction: "返回示意来源",
      steps: [
        { id: "source", label: "来源 / Source", title: "从可追问的主体与时间开始", body: "示意起点可以是一项项目任务、活动资料或现场反馈。这里没有真实门店或客户记录。" },
        { id: "evidence", label: "证据 / Evidence", title: "让每份材料都能回到来处", body: "保留来源、采集时间、上下文与核验状态。此演示没有接入外部来源，也不保存数据。" },
        { id: "event", label: "事件 / Event", title: "把变化放回时间脉络", body: "只有有依据可查的变化才进入事件，并保留前后时点与来源。本页面不声称现实中发生过变化。" },
        { id: "case", label: "事项 / Case", title: "把关联资料整理成待核实问题", body: "问题不等于结论。资料缺失、尚未采集或仍不确定的部分，会保持原有状态。" },
        { id: "insight", label: "洞察 / Insight", title: "让解释带着证据与不确定性", body: "实际洞察须由证据支持；此示意不计算经营或市场指标，也不生成真实洞察。" },
        { id: "decision", label: "决策 / Decision", title: "由有职责的人核对后作出判断", body: "判断应能追溯到相关资料、分析和仍待确认的事项。演示不替团队作决定。" },
        { id: "action", label: "行动 / Action", title: "经过权限与审批，再处理影响", body: "任何外部或重要写入都须通过现有权限与审批边界。这个公开示意不会发起操作。" },
        { id: "outcome", label: "结果 / Outcome", title: "记录实际发生的结果", body: "只有真实执行后由产品记录的结果，才能进入后续观察。这里没有模拟成功或捏造成效。" },
        { id: "evaluation", label: "评估 / Evaluation", title: "依据真实反馈复核并积累学习", body: "实际评估由明确目标、结果和来源支撑。此示意不含客户、经营或效果数据。" },
      ],
    },
    surfaces: {
      eyebrow: "四种表面，不是四个产品",
      title: "同一产品核心，各有清楚边界。",
      intro: "这些是各表面的职责说明，不代表服务已部署或每项能力都已开放。",
      public: {
        title: "Public Website",
        label: "当前页面",
        description: "介绍产品、展示虚构示意，并提供已配置的联系与入口。",
      },
      web: {
        title: "Web Workspace",
        label: "浏览器工作空间",
        description: "产品工作空间与本介绍网站分开；是否可进入取决于对应部署。",
      },
      desktop: {
        title: "Desktop App",
        label: "桌面应用",
        description:
          "浏览器自动化、设备本地 AI 与本机文件等能力依赖桌面环境；本网站不会模拟或执行它们。",
      },
      mobile: {
        title: "Mobile Companion",
        label: "移动伴侣",
        description: "独立的移动端表面，不是把本网站缩小，也不在此宣称已提供安装。",
      },
      note: "能力依赖各自的运行环境与部署状态；本页面不替它们背书。",
    },
    access: {
      eyebrow: "继续了解或联系",
      title: "入口应当真实可达。",
      intro: "试用、联系、帮助与工作空间地址由部署方分别配置；未配置时会明确显示状态。",
      configured: "此构建已连接一个公开入口。",
      unconfigured: "此构建尚未连接此入口。",
      trial: { title: "试用", action: "查看试用入口" },
      contact: { title: "联系", action: "前往联系页面" },
      help: { title: "帮助", action: "打开帮助中心" },
      workspace: { title: "工作空间", action: "进入产品工作空间" },
      helpStateId: "help-state",
      trialStateId: "trial-state",
      contactStateId: "contact-state",
      workspaceStateId: "workspace-state",
    },
    footer: {
      product: "序境 LUMENIS",
      note: "公开介绍页面。示意内容为虚构；本页面不持有或改变产品事实。",
      navigationLabel: "页脚导航",
    },
    status: {
      preview: "预览构建：搜索引擎索引已关闭。",
    },
  },
  en: {
    lang: "en",
    languageName: "English",
    productName: "LUMENIS",
    metadata: {
      title: "LUMENIS — Follow a trace, return to its source",
      description:
        "Meet LUMENIS: a product for commercial operations and brand-market work, connecting sourced material, decisions, content plans, and review.",
    },
    navigation: [
      { href: "#structure", label: "Product structure" },
      { href: "#scenarios", label: "Use cases" },
      { href: "#demo", label: "Illustrative demo" },
      { href: "#access", label: "Ways to access" },
    ],
    languageNavigationLabel: "Choose a language",
    primaryNavigationLabel: "Product introduction navigation",
    headerNote: "PRODUCT EXPLORATION",
    skipLabel: "Skip to main content",
    hero: {
      eyebrow: "One trace, more than one destination",
      title: "Follow change. See where it came from and where it leads.",
      description:
        "For commercial operations and brand-market teams: keep sourced material, open questions, business decisions, and deliverables in one continuous line of work.",
      primary: "Explore an illustrative trace",
      secondary: "See how the product is shaped",
      note: "This is a public product introduction. Its example is fictional and uses no live product data.",
      diagramLabel: "From sourced material to business delivery, then use feedback to improve the next plan.",
      flowLabels: { material: "Material", delivery: "Delivery", feedback: "Feedback" },
    },
    sequence: {
      heading: "From material to delivery, then review",
      intro: "Keep each step grounded in source material, a clear question, a reasoned decision, and actual feedback.",
      returnLabel: "Use delivery feedback to refine the next plan.",
      nodes: [
        { name: "Material", english: "MATERIAL", meaning: "Keep source, date, and context together" },
        { name: "Question", english: "QUESTION", meaning: "Turn gaps into questions to verify" },
        { name: "Decision", english: "DECISION", meaning: "Compare evidence before choosing a next step" },
        { name: "Plan", english: "PLAN", meaning: "Set out the work to be done" },
        { name: "Delivery", english: "DELIVERY", meaning: "Produce work the team can use" },
        { name: "Review", english: "REVIEW", meaning: "Use feedback to improve the next plan" },
      ],
    },
    structure: {
      eyebrow: "One product, four responsibilities",
      title: "Start with where the question lives.",
      intro: "One product core, with distinct entry points for each domain. Shared creation and system foundations support them all.",
      commerce: {
        ordinal: "01 / Commercial operations",
        title: "Start with a subject and time",
        description:
          "Check real resources and changes across projects, stores, events, and customer feedback; carry the evidence into operational decisions and next tasks.",
        lens: "Subject → time → causal trace",
      },
      brand: {
        ordinal: "02 / Brand and market",
        title: "Start with a brand and its relationships",
        description:
          "Compare consumer needs, competitors, and channels to support choices about brand expression, content, and partners.",
        lens: "Brand → relationships → propagation",
      },
      shared: {
        ordinal: "03 / Shared capabilities",
        title: "Creation, research, and evaluation—together",
        description:
          "Carry research into briefs, content, reports, and evaluation while retaining sources, open questions, and actual feedback.",
      },
      system: {
        ordinal: "04 / System foundations",
        title: "Keep foundational responsibilities in their place",
        description:
          "Collection, runtime, scheduling, security, and recovery support the product without replacing its business domains.",
      },
    },
    scenarios: {
      eyebrow: "Begin with a real question",
      title: "Make the next question traceable.",
      intro: "These are representative questions for LUMENIS—not customer stories or claims of outcome.",
      commerce: {
        title: "From on-site resources to a content plan",
        question: "Which resources merit coverage next month, and what must stores confirm?",
        description:
          "Check project directories, brand updates, and on-site material. Separate verified resources from open questions before planning content.",
        path: ["Project task", "Check resources", "Plan content", "Keep sources"],
      },
      brand: {
        title: "From market research to a brand brief",
        question: "Who is a new range for, and which content and partners fit?",
        description:
          "Compare consumer situations, competitors, channels, and creator material. Carry supported choices and unknowns into the brief.",
        path: ["Brand task", "Compare evidence", "Choose content", "Open questions"],
      },
    },
    demo: {
      eyebrow: "A product example you can inspect",
      title: "From source to action, every step stays traceable.",
      intro:
        "Drag the timeline or use the arrow keys to explore the LUMENIS business chain. This is a clearly labelled structural illustration: no live data, customer records, or completed actions are shown.",
      illustrativeLabel: "Fictional example · not live data",
      sourceLabel: "Point / fictional source",
      changeLabel: "Change / timeline",
      traceLabel: "Connection / trace",
      returnLabel: "Return / source context",
      commerce: {
        title: "Subject and time: a planning change",
        source: "Illustrative note: the expected duration for a plan has changed.",
        change: "Place the change in context over time without inferring a cause.",
        trace: "Connect related questions to check, keeping them as questions rather than conclusions.",
        back: "Return to this fictional planning note",
        sourceId: "example-source-commerce",
      },
      brand: {
        title: "Brand and relationships: a topic in motion",
        source: "Illustrative note: a brand topic appears in a market context.",
        change: "Consider how it may relate to other contexts.",
        trace: "Follow the possible connections; this example is not a real monitoring or propagation result.",
        back: "Return to this fictional topic note",
        sourceId: "example-source-brand",
      },
      returnNote: "Return to the source to inspect its context and supporting evidence.",
      contextLabel: "Illustrative scene / Commercial operations",
      timelineLabel: "Business chain timeline",
      timelineHeading: "Follow material toward an outcome",
      scrubberLabel: "Choose a business-chain step",
      scrubberHelp: "Drag the slider or use the left and right arrow keys to browse each step.",
      focusLabel: "Focused step",
      viewModeLabel: "Illustration layout",
      linearView: "Linear timeline",
      orbitView: "Orbit view",
      returnAction: "Return to illustrative source",
      steps: [
        { id: "source", label: "Source", title: "Start with a subject and a point in time", body: "An illustrative starting point could be a project task, event material, or field note. No real store or customer record appears here." },
        { id: "evidence", label: "Evidence", title: "Keep every material linked to its origin", body: "Retain source, capture time, context, and verification state. This demo connects to no external source and stores nothing." },
        { id: "event", label: "Event", title: "Place change back on its timeline", body: "Only an evidenced change becomes an event, with its before-and-after context intact. This page does not claim a real event occurred." },
        { id: "case", label: "Case", title: "Group related material into a question to check", body: "A question is not a conclusion. Missing, uncollected, and uncertain information keeps its original state." },
        { id: "insight", label: "Insight", title: "Keep evidence and uncertainty beside interpretation", body: "A real insight must be supported by Evidence. This illustration calculates no commercial or market metrics and produces no live insight." },
        { id: "decision", label: "Decision", title: "Let the responsible person review before deciding", body: "A decision remains traceable to relevant material, analysis, and open questions. This demo makes no decision for a team." },
        { id: "action", label: "Action", title: "Pass permission and approval before an effect", body: "External or consequential writes still pass through the existing Permission and approval boundary. This public illustration triggers no action." },
        { id: "outcome", label: "Outcome", title: "Record what actually happened", body: "Only an outcome recorded by the product after real execution can be reviewed. No success or result is simulated here." },
        { id: "evaluation", label: "Evaluation", title: "Review against real feedback and carry learning forward", body: "A real evaluation uses defined goals, outcomes, and sources. This illustration contains no customer, operational, or performance data." },
      ],
    },
    surfaces: {
      eyebrow: "Four surfaces, not four products",
      title: "One product core, clear boundaries.",
      intro: "These describe the role of each surface, not a claim that a service is deployed or every capability is available.",
      public: {
        title: "Public Website",
        label: "This page",
        description: "Explains the product, shows fictional examples, and offers configured public destinations.",
      },
      web: {
        title: "Web Workspace",
        label: "Browser workspace",
        description: "The product workspace is separate from this introduction; access depends on its deployment.",
      },
      desktop: {
        title: "Desktop App",
        label: "Desktop application",
        description:
          "Browser automation, device-local AI, and local files depend on a desktop environment. This website does not simulate or run them.",
      },
      mobile: {
        title: "Mobile Companion",
        label: "Mobile companion",
        description: "A distinct mobile surface—not this website shrunk down, and no installation is claimed here.",
      },
      note: "Capabilities depend on their own runtime and deployment; this page does not imply availability.",
    },
    access: {
      eyebrow: "Continue or get in touch",
      title: "An entry point should lead somewhere real.",
      intro: "Trial, contact, help, and workspace destinations are configured separately by deployment. Unconfigured routes are labeled clearly.",
      configured: "A public destination is connected for this build.",
      unconfigured: "No destination is connected for this build.",
      trial: { title: "Trial", action: "View trial destination" },
      contact: { title: "Contact", action: "Go to contact" },
      help: { title: "Help", action: "Open help center" },
      workspace: { title: "Workspace", action: "Enter the product workspace" },
      helpStateId: "help-state",
      trialStateId: "trial-state",
      contactStateId: "contact-state",
      workspaceStateId: "workspace-state",
    },
    footer: {
      product: "LUMENIS",
      note: "Public product introduction. The example is fictional; this page does not own or change product truth.",
      navigationLabel: "Footer navigation",
    },
    status: {
      preview: "Preview build: search indexing is disabled.",
    },
  },
  ko: {
    lang: "ko",
    languageName: "한국어",
    productName: "서경 LUMENIS",
    metadata: {
      title: "서경 LUMENIS | 흔적을 따라가고, 출발점으로 돌아오다",
      description:
        "서경 LUMENIS를 소개합니다. 상업 운영과 브랜드·시장 업무에서 출처가 있는 자료, 판단, 콘텐츠 계획과 회고를 연결합니다.",
    },
    navigation: [
      { href: "#structure", label: "제품 구조" },
      { href: "#scenarios", label: "사용 맥락" },
      { href: "#demo", label: "예시 보기" },
      { href: "#access", label: "이용 방법" },
    ],
    languageNavigationLabel: "언어 선택",
    primaryNavigationLabel: "제품 소개 탐색",
    headerNote: "제품 탐색",
    skipLabel: "본문으로 건너뛰기",
    hero: {
      eyebrow: "하나의 흔적, 여러 갈래의 맥락",
      title: "변화를 따라가며, 시작과 다음을 봅니다.",
      description:
        "상업 운영과 브랜드·시장 팀을 위해 출처가 있는 자료, 확인할 질문, 업무 판단과 결과물을 하나의 작업 흐름으로 연결합니다.",
      primary: "예시 흔적 살펴보기",
      secondary: "제품 구조 알아보기",
      note: "이 페이지는 제품 소개입니다. 예시는 허구이며 실제 제품 데이터를 사용하지 않습니다.",
      diagramLabel: "자료를 정리해 업무 결과로 전달하고, 피드백을 바탕으로 다음 계획을 다듬습니다.",
      flowLabels: { material: "자료", delivery: "전달", feedback: "피드백" },
    },
    sequence: {
      heading: "자료에서 전달까지, 결과를 다시 살핍니다",
      intro: "각 단계는 확인할 수 있는 자료, 분명한 질문, 근거 있는 판단과 실제 피드백을 잇습니다.",
      returnLabel: "전달 결과와 피드백을 자료에 다시 대조해 다음 계획을 다듬습니다.",
      nodes: [
        { name: "자료", english: "MATERIAL", meaning: "출처·시점·맥락을 함께 보존합니다" },
        { name: "질문", english: "QUESTION", meaning: "확인할 사항과 정보의 공백을 나눕니다" },
        { name: "판단", english: "DECISION", meaning: "근거를 비교해 다음 방향을 정합니다" },
        { name: "계획", english: "PLAN", meaning: "다음에 할 일을 구체적으로 정리합니다" },
        { name: "전달", english: "DELIVERY", meaning: "팀이 활용할 결과물로 이어갑니다" },
        { name: "되돌아보기", english: "REVIEW", meaning: "실제 피드백을 다음 계획에 반영합니다" },
      ],
    },
    structure: {
      eyebrow: "하나의 제품, 네 가지 역할",
      title: "질문이 어디서 시작되는지 봅니다.",
      intro: "하나의 제품 코어 안에 영역별 관점을 두고, 공동 창작과 시스템 기반이 이를 뒷받침합니다.",
      commerce: {
        ordinal: "01 / 상업 운영",
        title: "대상과 시간에서 시작합니다",
        description:
          "프로젝트, 매장, 행사와 고객 피드백의 실제 자원과 변화를 확인하고 근거 있는 운영 판단과 다음 할 일로 이어갑니다.",
        lens: "대상 → 시간 → 인과의 흔적",
      },
      brand: {
        ordinal: "02 / 브랜드와 시장",
        title: "브랜드와 관계에서 시작합니다",
        description:
          "소비자 수요, 경쟁 브랜드와 채널 변화를 비교해 브랜드 표현, 콘텐츠 방향과 협업 선택의 근거를 정리합니다.",
        lens: "브랜드 → 관계 → 확산의 흐름",
      },
      shared: {
        ordinal: "03 / 공동 역량",
        title: "창작, 연구, 평가가 함께 자랍니다",
        description:
          "연구 결과를 브리프, 콘텐츠, 보고서와 평가로 이어가며 출처, 미확인 사항과 실제 피드백을 남깁니다.",
      },
      system: {
        ordinal: "04 / 시스템 기반",
        title: "기반 역할은 제자리에 둡니다",
        description:
          "수집, 실행, 일정 관리, 보안과 복구는 기반을 이루며 업무 영역을 대신하지 않습니다.",
      },
    },
    scenarios: {
      eyebrow: "실제 질문에서 시작하기",
      title: "다음 질문에 이르는 과정을 따라갑니다.",
      intro: "아래는 서경의 관점에 맞는 대표적인 질문이며, 고객 사례나 성과 약속이 아닙니다.",
      commerce: {
        title: "현장 자원에서 콘텐츠 계획까지",
        question: "다음 달 어떤 자원을 취재하고, 매장에 무엇을 확인해야 할까요?",
        description:
          "프로젝트 목록, 브랜드 소식과 현장 자료를 확인하고 검증된 자원과 미확인 정보를 구분해 콘텐츠 계획의 근거로 삼습니다.",
        path: ["프로젝트 과제", "자원 확인", "콘텐츠 계획", "근거 보존"],
      },
      brand: {
        title: "시장 조사에서 브랜드 브리프까지",
        question: "신제품은 누구에게, 어떤 콘텐츠와 협업으로 전해야 할까요?",
        description:
          "소비자 상황, 경쟁사, 채널과 크리에이터 자료를 비교해 근거 있는 선택과 미확인 사항을 브리프에 담습니다.",
        path: ["브랜드 과제", "근거 비교", "콘텐츠 선택", "미확인 사항"],
      },
    },
    demo: {
      eyebrow: "살펴볼 수 있는 제품 예시",
      title: "출처부터 실행까지, 모든 단계를 따라갑니다.",
      intro:
        "타임라인을 드래그하거나 키보드 방향키로 서경의 업무 흐름을 살펴보세요. 이 페이지는 구조를 설명하는 허구의 예시이며 실시간 데이터, 고객 기록 또는 완료된 실행을 보여주지 않습니다.",
      illustrativeLabel: "허구의 예시 · 실시간 데이터 아님",
      sourceLabel: "점 / 가상의 출처",
      changeLabel: "변화 / 시간축",
      traceLabel: "연결 / 흔적",
      returnLabel: "돌아가기 / 출처 맥락",
      commerce: {
        title: "대상과 시간: 계획 변경",
        source: "예시 기록: 계획의 예상 기간이 변경되었습니다.",
        change: "원인을 추측하지 않고 시간에 따른 맥락 안에 변화를 놓습니다.",
        trace: "확인할 관련 질문을 연결하되 결론이 아닌 질문으로 남깁니다.",
        back: "이 가상의 계획 기록으로 돌아가기",
        sourceId: "example-source-commerce",
      },
      brand: {
        title: "브랜드와 관계: 움직이는 주제",
        source: "예시 기록: 브랜드 주제가 하나의 시장 맥락에 나타납니다.",
        change: "다른 맥락과 어떤 관계가 있을지 살펴봅니다.",
        trace: "가능한 연결을 따라갑니다. 실제 모니터링이나 확산 결과가 아닙니다.",
        back: "이 가상의 주제 기록으로 돌아가기",
        sourceId: "example-source-brand",
      },
      returnNote: "출처로 돌아가 맥락과 근거를 확인합니다.",
      contextLabel: "예시 장면 / 상업 운영",
      timelineLabel: "업무 흐름 타임라인",
      timelineHeading: "자료에서 결과까지 따라가기",
      scrubberLabel: "업무 흐름 단계 선택",
      scrubberHelp: "슬라이더를 드래그하거나 왼쪽·오른쪽 방향키로 단계를 살펴보세요.",
      focusLabel: "현재 단계",
      viewModeLabel: "예시 배치 방식",
      linearView: "선형 타임라인",
      orbitView: "원형 탐색",
      returnAction: "예시 출처로 돌아가기",
      steps: [
        { id: "source", label: "출처 / Source", title: "대상과 시점에서 시작합니다", body: "예시의 출발점은 프로젝트 과제, 행사 자료 또는 현장 메모일 수 있습니다. 실제 매장이나 고객 기록은 포함하지 않습니다." },
        { id: "evidence", label: "증거 / Evidence", title: "모든 자료를 출처와 연결합니다", body: "출처, 수집 시점, 맥락과 검증 상태를 보존합니다. 이 데모는 외부 출처에 연결하거나 데이터를 저장하지 않습니다." },
        { id: "event", label: "이벤트 / Event", title: "변화를 시간의 흐름에 놓습니다", body: "근거가 확인된 변화만 이벤트가 되며 전후 맥락을 보존합니다. 이 페이지는 실제 변화가 있었다고 주장하지 않습니다." },
        { id: "case", label: "사안 / Case", title: "관련 자료를 확인할 질문으로 묶습니다", body: "질문은 결론이 아닙니다. 누락, 미수집, 불확실한 정보는 본래 상태 그대로 남습니다." },
        { id: "insight", label: "인사이트 / Insight", title: "해석과 근거, 불확실성을 함께 둡니다", body: "실제 인사이트는 근거로 뒷받침되어야 합니다. 이 예시는 상업·시장 지표를 계산하거나 실제 인사이트를 만들지 않습니다." },
        { id: "decision", label: "의사결정 / Decision", title: "담당자가 검토한 뒤 판단합니다", body: "판단은 관련 자료, 분석, 미확인 질문으로 거슬러 올라갈 수 있어야 합니다. 이 데모는 팀 대신 결정하지 않습니다." },
        { id: "action", label: "실행 / Action", title: "영향을 주기 전에 권한과 승인을 거칩니다", body: "외부 변경이나 중요한 쓰기는 기존 Permission 및 승인 경계를 통과해야 합니다. 이 공개 예시는 어떤 작업도 실행하지 않습니다." },
        { id: "outcome", label: "결과 / Outcome", title: "실제로 일어난 결과를 기록합니다", body: "실제 실행 후 제품이 기록한 결과만 검토할 수 있습니다. 여기서는 성공이나 결과를 시뮬레이션하지 않습니다." },
        { id: "evaluation", label: "평가 / Evaluation", title: "실제 피드백으로 검토하고 학습합니다", body: "실제 평가는 정의된 목표, 결과와 출처를 사용합니다. 이 예시에는 고객, 운영 또는 성과 데이터가 없습니다." },
      ],
    },
    surfaces: {
      eyebrow: "네 가지 표면, 네 개의 제품이 아닙니다",
      title: "하나의 제품 코어, 분명한 경계.",
      intro: "각 표면의 역할을 설명하며, 서비스 배포나 모든 기능의 제공을 뜻하지 않습니다.",
      public: {
        title: "Public Website",
        label: "현재 페이지",
        description: "제품을 소개하고 허구의 예시를 보여주며 설정된 공개 경로를 제공합니다.",
      },
      web: {
        title: "Web Workspace",
        label: "브라우저 작업 공간",
        description: "제품 작업 공간은 소개 사이트와 분리되며, 접근 가능 여부는 배포 상태에 따라 다릅니다.",
      },
      desktop: {
        title: "Desktop App",
        label: "데스크톱 앱",
        description:
          "브라우저 자동화, 기기 내 AI, 로컬 파일은 데스크톱 환경에 따라 다릅니다. 이 웹사이트는 이를 흉내 내거나 실행하지 않습니다.",
      },
      mobile: {
        title: "Mobile Companion",
        label: "모바일 동반 앱",
        description: "별도의 모바일 표면입니다. 웹사이트의 축소판이 아니며 여기서 설치 가능하다고 말하지 않습니다.",
      },
      note: "역량은 각 실행 환경과 배포 상태에 따라 다르며, 이 페이지는 제공 여부를 암시하지 않습니다.",
    },
    access: {
      eyebrow: "더 알아보거나 문의하기",
      title: "실제 목적지로 이어지는 입구.",
      intro: "체험, 문의, 도움말, 작업 공간 주소는 배포별로 설정됩니다. 설정되지 않은 경로는 그대로 표시합니다.",
      configured: "이 빌드에는 공개 목적지가 연결되어 있습니다.",
      unconfigured: "이 빌드에는 연결된 목적지가 없습니다.",
      trial: { title: "체험", action: "체험 경로 보기" },
      contact: { title: "문의", action: "문의 페이지로 이동" },
      help: { title: "도움말", action: "도움말 열기" },
      workspace: { title: "작업 공간", action: "제품 작업 공간으로 이동" },
      helpStateId: "help-state",
      trialStateId: "trial-state",
      contactStateId: "contact-state",
      workspaceStateId: "workspace-state",
    },
    footer: {
      product: "서경 LUMENIS",
      note: "공개 제품 소개 페이지입니다. 예시는 허구이며, 이 페이지는 제품의 사실을 소유하거나 변경하지 않습니다.",
      navigationLabel: "바닥글 탐색",
    },
    status: {
      preview: "미리보기 빌드: 검색 색인이 차단되어 있습니다.",
    },
  },
} as const;

export function isLocale(value: string): value is Locale {
  return locales.includes(value as Locale);
}
