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
    skipLabel: "跳到主要内容",
    hero: {
      eyebrow: "一条线索，不止一个终点",
      title: "沿着变化，看见来处与去向。",
      description:
        "面向商业运营与品牌市场团队，把有来源的资料、待核实的问题、业务判断和交付物放在同一条工作脉络里。",
      primary: "看一段示意线索",
      secondary: "了解产品结构",
      note: "本页是产品介绍；示意内容为虚构，不连接真实产品数据。",
      diagramLabel: "从点出发，经由轴、迹、场、层与界，并返回起点。",
    },
    sequence: {
      heading: "序境的观察方式",
      intro: "不是把信息堆在一起，而是让关系有迹可循。",
      returnLabel: "循迹返回原点",
      nodes: [
        { name: "点", english: "POINT", meaning: "一个可追问的起点" },
        { name: "轴", english: "AXIS", meaning: "变化所在的时间与方向" },
        { name: "迹", english: "TRACE", meaning: "关联如何逐步形成" },
        { name: "场", english: "FIELD", meaning: "线索所处的关系网络" },
        { name: "层", english: "STRATA", meaning: "不同职责彼此承托" },
        { name: "界", english: "BOUNDARY", meaning: "能力与责任的边界" },
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
      title: "看一条线索怎样走，也怎样回来。",
      intro:
        "下面的情境与文字均为专门创作的虚构示例，只说明关系结构；不是实时数据、真实客户记录，也不会触发产品操作。",
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
      returnNote: "返回起点，是理解线索的一部分。",
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
    skipLabel: "Skip to main content",
    hero: {
      eyebrow: "One trace, more than one destination",
      title: "Follow change. See where it came from and where it leads.",
      description:
        "For commercial operations and brand-market teams: keep sourced material, open questions, business decisions, and deliverables in one continuous line of work.",
      primary: "Explore an illustrative trace",
      secondary: "See how the product is shaped",
      note: "This is a public product introduction. Its example is fictional and uses no live product data.",
      diagramLabel: "Start at a point, move through axis, trace, field, strata, and boundary, then return to the point.",
    },
    sequence: {
      heading: "A way of seeing",
      intro: "Not information piled together, but relationships you can follow.",
      returnLabel: "Trace back to the point",
      nodes: [
        { name: "Point", english: "POINT", meaning: "A starting point worth asking about" },
        { name: "Axis", english: "AXIS", meaning: "Time and direction of change" },
        { name: "Trace", english: "TRACE", meaning: "How a relationship takes shape" },
        { name: "Field", english: "FIELD", meaning: "The network around a trace" },
        { name: "Strata", english: "STRATA", meaning: "Distinct responsibilities, held together" },
        { name: "Boundary", english: "BOUNDARY", meaning: "Where a capability begins and ends" },
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
      title: "Follow a trace forward—and back again.",
      intro:
        "Every situation and line below is a fictional example written to explain relationships. It is not live data, a real customer record, or a product action.",
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
      returnNote: "Returning to the starting point is part of understanding the trace.",
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
    skipLabel: "본문으로 건너뛰기",
    hero: {
      eyebrow: "하나의 흔적, 여러 갈래의 맥락",
      title: "변화를 따라가며, 시작과 다음을 봅니다.",
      description:
        "상업 운영과 브랜드·시장 팀을 위해 출처가 있는 자료, 확인할 질문, 업무 판단과 결과물을 하나의 작업 흐름으로 연결합니다.",
      primary: "예시 흔적 살펴보기",
      secondary: "제품 구조 알아보기",
      note: "이 페이지는 제품 소개입니다. 예시는 허구이며 실제 제품 데이터를 사용하지 않습니다.",
      diagramLabel: "점에서 시작해 축, 흔적, 장, 층위, 경계를 지나 출발점으로 돌아옵니다.",
    },
    sequence: {
      heading: "서경이 살펴보는 방식",
      intro: "정보를 쌓아 두기보다 관계를 따라갈 수 있게 합니다.",
      returnLabel: "흔적을 따라 출발점으로",
      nodes: [
        { name: "점", english: "POINT", meaning: "질문을 시작할 한 지점" },
        { name: "축", english: "AXIS", meaning: "변화의 시간과 방향" },
        { name: "흔적", english: "TRACE", meaning: "관계가 만들어지는 과정" },
        { name: "장", english: "FIELD", meaning: "흔적을 둘러싼 관계망" },
        { name: "층위", english: "STRATA", meaning: "서로 다른 역할의 기반" },
        { name: "경계", english: "BOUNDARY", meaning: "역량이 시작되고 끝나는 곳" },
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
      title: "흔적을 따라간 뒤 다시 돌아옵니다.",
      intro:
        "아래의 상황과 문구는 관계 구조를 설명하기 위해 작성한 허구의 예시입니다. 실시간 데이터나 실제 고객 기록이 아니며 제품 동작을 실행하지 않습니다.",
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
      returnNote: "출발점으로 돌아오는 것 또한 흔적을 이해하는 과정입니다.",
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
