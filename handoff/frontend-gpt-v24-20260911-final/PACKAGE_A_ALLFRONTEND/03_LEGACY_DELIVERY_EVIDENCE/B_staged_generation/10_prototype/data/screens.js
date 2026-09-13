/* AUTO-GENERATED — runtime subset (no viewmodel/binding/contract keys) */
window.LUM_SCREENS = {
  "ACC-01": {
    "titleKey": "screen.ACC-01",
    "chrome": "none",
    "sections": [
      {
        "type": "raw",
        "html": "<div style=\"min-height:78vh;display:grid;place-items:center\" data-reveal>\n   <div class=\"lum-opt lum-opt-composer\" data-opt=\"composer\" data-strength=\"idle\" style=\"max-width:440px;width:100%\">\n     <canvas class=\"lum-opt__gl\"></canvas><div class=\"lum-opt__fallback\"></div>\n     <div style=\"padding:28px\" class=\"lum-stack-4\">\n       <div class=\"lum-row\" style=\"gap:10px\"><div class=\"lum-rail__logo\" style=\"width:40px;height:40px\">序</div>\n         <div><b class=\"lum-h3\" data-i18n=\"product.mother\">序境 LUMENIS</b><div class=\"lum-caption\" data-i18n=\"acc.signin_sub\"></div></div></div>\n       <div class=\"lum-field\"><label class=\"lum-label\" data-i18n=\"acc.choose_domain\"></label>\n         <div class=\"lum-segmented\" style=\"width:100%\"><button aria-pressed=\"true\">商业运营</button><button aria-pressed=\"false\">品牌市场</button></div></div>\n       <div class=\"lum-field\"><label class=\"lum-label\">Enterprise Account</label><input class=\"lum-input\" placeholder=\"name@company.com\"></div>\n       <div class=\"lum-field\"><label class=\"lum-label\">Password</label><input class=\"lum-input\" type=\"password\" placeholder=\"••••••••\"></div>\n       <button class=\"lum-btn lum-btn-primary\" style=\"width:100%;justify-content:center\" data-i18n=\"acc.sso\"></button>\n       <div class=\"lum-row-between lum-caption\"><span data-i18n=\"acc.recovery\"></span><span>SAML / SSO</span></div>\n     </div></div></div>"
      }
    ],
    "context": {
      "evidence": []
    }
  },
  "ACC-02": {
    "titleKey": "screen.ACC-02",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Entry",
        "title": "主体选择与领域视角",
        "titleKey": "screen.ACC-02",
        "desc": "先选 Subject（主体）再进入领域视角；选择只改变工作上下文，不改变数据归属，后端重验授权。"
      },
      {
        "type": "cards",
        "items": [
          {
            "title": "广州太古汇",
            "desc": "商业综合体 · mall_group",
            "ico": "target",
            "badge": {
              "text": "最近使用",
              "cls": "brand"
            },
            "action": {
              "label": "进入",
              "variant": "primary",
              "id": "",
              "cls": "NAVIGATION",
              "scope": "UNKNOWN",
              "target": "UNKNOWN",
              "permission": "UNKNOWN",
              "size": "sm"
            }
          },
          {
            "title": "广州太古汇·北区",
            "desc": "业务单元 · wing",
            "ico": "layers"
          },
          {
            "title": "Dior（场内品牌）",
            "desc": "品牌主体",
            "ico": "campaign"
          },
          {
            "title": "2026 春季会员日",
            "desc": "Campaign 主体",
            "ico": "campaign"
          }
        ],
        "cols": 2
      },
      {
        "type": "split",
        "main": [
          {
            "type": "note",
            "text": "SubjectContext 八字段：subject_id / subject_type / domain / scope / permissions / time_window / locale / context_version。切换主体不重写 Canonical 归属。",
            "kind": "RULE",
            "code": "SUBJECT-8"
          }
        ],
        "side": [
          {
            "type": "form",
            "title": "默认视角",
            "fields": [
              {
                "label": "默认领域",
                "type": "select",
                "ph": "",
                "opts": [
                  "商业运营",
                  "品牌市场"
                ]
              },
              {
                "label": "默认时间窗",
                "type": "select",
                "ph": "",
                "opts": [
                  "近7天",
                  "近30天",
                  "近90天"
                ]
              },
              {
                "label": "界面语言",
                "type": "select",
                "ph": "",
                "opts": [
                  "简体中文",
                  "English",
                  "한국어"
                ]
              }
            ],
            "actions": [
              {
                "label": "设为默认并进入",
                "variant": "primary",
                "id": "enter",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "ico": "check"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "SubjectContext v2.1"
      ]
    }
  },
  "ACC-03": {
    "titleKey": "screen.ACC-03",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Entry",
        "title": "全局工作空间启动",
        "titleKey": "screen.ACC-03",
        "desc": "从统一入口进入各领域与 AI；底部 Dock 承载一级目的地与中央 AI 入口。"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "待办",
            "value": 6,
            "icon": "bell",
            "source": "SH-06",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "在办事件",
            "value": 9,
            "icon": "event",
            "source": "CTH-04",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "进行中 Campaign",
            "value": 4,
            "icon": "campaign",
            "source": "BMP-07",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "证据新增(24h)",
            "value": 312,
            "icon": "link",
            "source": "SH-02",
            "fresh": "live",
            "decimals": 0,
            "delta": 8,
            "deltaUnit": "%"
          }
        ]
      },
      {
        "type": "cards",
        "items": [
          {
            "title": "进入商业运营",
            "desc": "总览/监测/事件/风险/报告",
            "ico": "compass",
            "action": {
              "label": "进入",
              "variant": "secondary",
              "id": "",
              "cls": "NAVIGATION",
              "scope": "UNKNOWN",
              "target": "UNKNOWN",
              "permission": "UNKNOWN",
              "size": "sm"
            }
          },
          {
            "title": "进入品牌市场",
            "desc": "品牌/传播/创作者/播客",
            "ico": "campaign"
          },
          {
            "title": "问 AI Composer",
            "desc": "沿证据链得到结论",
            "ico": "sparkles",
            "badge": {
              "text": "AI",
              "cls": "brand"
            }
          },
          {
            "title": "继续未完成",
            "desc": "周报 W37 草稿 / Case-221",
            "ico": "folder"
          }
        ],
        "cols": 4
      },
      {
        "type": "runtime",
        "title": "启动检查",
        "items": [
          {
            "name": "运行时身份",
            "state": "ok",
            "detail": "/api/runtime/identity"
          },
          {
            "name": "数据库隔离",
            "state": "ok",
            "detail": "ZBC_DB_PATH"
          },
          {
            "name": "权限上下文",
            "state": "ok",
            "detail": "已加载"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "启动链 runtime identity"
      ]
    }
  },
  "ACC-04": {
    "titleKey": "screen.ACC-04",
    "chrome": "none",
    "sections": [
      {
        "type": "raw",
        "html": "<div style=\"min-height:78vh;display:grid;place-items:center\" data-reveal>\n   <div class=\"lum-card lum-card-pad\" style=\"max-width:460px;width:100%\" class2=\"\">\n     <span class=\"lum-badge lum-badge-warning\">Auth Guard</span>\n     <h2 class=\"lum-h3\" style=\"margin:10px 0 6px\" data-i18n=\"acc.recovery\">账号恢复</h2>\n     <p class=\"lum-body-2\">当权限不足、会话过期或主体未授权时进入此守卫：说明原因、给出可执行的恢复路径，不静默降级为假数据。</p>\n     <div class=\"lum-stack-2\" style=\"margin-top:14px\">\n       <div class=\"lum-action-item\"><span class=\"lum-action-item__ico\">①</span><span class=\"lum-action-item__txt\"><b>重新验证企业身份</b><span>SAML / SSO 重新登录</span></span></div>\n       <div class=\"lum-action-item\"><span class=\"lum-action-item__ico\">②</span><span class=\"lum-action-item__txt\"><b>申请 Subject/Scope 授权</b><span>走审批，不绕过权限边界</span></span></div>\n       <div class=\"lum-action-item\"><span class=\"lum-action-item__ico\">③</span><span class=\"lum-action-item__txt\"><b>联系管理员并附带 Trace ID</b><span>问题可追溯</span></span></div></div>\n     <div class=\"lum-row\" style=\"margin-top:14px\"><button class=\"lum-btn lum-btn-primary\" data-i18n=\"acc.sso\"></button><button class=\"lum-btn lum-btn-ghost\" data-i18n=\"common.back\"></button></div>\n   </div></div>"
      }
    ],
    "context": {
      "evidence": []
    }
  },
  "CTH-01": {
    "titleKey": "screen.CTH-01",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 序境·商业运营",
        "title": "商业运营总览",
        "titleKey": "screen.CTH-01",
        "desc": "以当前 Subject 为上下文：核心指标 → 趋势 → 事件/证据 → 洞察 → 决策行动，全部可追溯。",
        "actions": [
          {
            "label": "生成运营简报",
            "variant": "primary",
            "id": "draft-brief",
            "cls": "DRAFT",
            "scope": "subject:current",
            "target": "report",
            "permission": "report:write",
            "ico": "report"
          },
          {
            "label": "切换时间范围",
            "variant": "secondary",
            "id": "",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "calendar"
          },
          {
            "label": "导出",
            "variant": "ghost",
            "id": "export-overview",
            "cls": "QUERY",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "download"
          }
        ]
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "今日到店客流",
            "value": 38214,
            "icon": "production",
            "source": "EV: footfall.canonical",
            "fresh": "live",
            "decimals": 0,
            "delta": 6.2,
            "deltaUnit": "%",
            "spark": [
              8,
              10,
              9,
              13,
              12,
              15,
              14,
              18,
              16,
              20,
              19,
              22
            ]
          },
          {
            "label": "会员销售占比",
            "value": 41.8,
            "icon": "trend",
            "source": "EV: sales.canonical",
            "fresh": "live",
            "decimals": 1,
            "unit": "%",
            "delta": 2.1,
            "deltaUnit": "%",
            "spark": [
              12,
              18,
              15,
              22,
              19,
              26,
              24
            ]
          },
          {
            "label": "在线负面声量",
            "value": 46,
            "icon": "risk",
            "source": "EV: sentiment.canonical",
            "fresh": "live",
            "decimals": 0,
            "delta": -12,
            "deltaUnit": "",
            "spark": [
              20,
              17,
              22,
              19,
              25,
              21,
              28
            ]
          },
          {
            "label": "在办事件",
            "value": 9,
            "icon": "event",
            "source": "EV: event.open",
            "fresh": "m5",
            "decimals": 0
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "近 30 天客流 vs 销售指数",
            "kind": "line",
            "series": [
              {
                "data": [
                  62,
                  66,
                  64,
                  70,
                  74,
                  71,
                  78,
                  82,
                  80,
                  86,
                  90,
                  88
                ],
                "color": "var(--lum-c-brand-500)"
              },
              {
                "data": [
                  40,
                  44,
                  43,
                  49,
                  52,
                  50,
                  55,
                  58,
                  57,
                  61,
                  65,
                  63
                ],
                "color": "var(--lum-c-success)"
              }
            ],
            "labels": [
              "9/2",
              "9/5",
              "9/8",
              "9/11",
              "9/14",
              "9/17",
              "9/20",
              "9/23",
              "9/26",
              "9/29",
              "10/2",
              "10/5"
            ],
            "legend": [
              {
                "label": "客流指数",
                "color": "var(--lum-c-brand-500)"
              },
              {
                "label": "销售指数",
                "color": "var(--lum-c-success)"
              }
            ]
          },
          {
            "type": "events",
            "title": "最新事件",
            "items": [
              {
                "time": "10:22",
                "title": "北区 18–21 点离场排队回升",
                "desc": "停车相关讨论 +24，风险分上行。",
                "date": "09-10",
                "level": "high",
                "tags": [
                  "停车",
                  "北区"
                ],
                "evidence": "EV-7710"
              },
              {
                "time": "09:05",
                "title": "新品牌快闪开业",
                "desc": "L2 西区快闪首日客流 +31%。",
                "date": "09-10",
                "level": "low",
                "tags": [
                  "品牌",
                  "活动"
                ],
                "evidence": "EV-7706"
              },
              {
                "time": "昨日",
                "title": "会员日 Campaign 复盘归档",
                "desc": "ROI 1:4.2，证据已归档。",
                "date": "09-09",
                "level": "low",
                "tags": [
                  "Campaign"
                ],
                "evidence": "EV-7688"
              }
            ],
            "more": true
          },
          {
            "type": "evidence",
            "title": "关键证据链",
            "items": [
              {
                "kind": "Metric",
                "id": "EV-7701",
                "chain": [
                  "Source",
                  "Canonical",
                  "Metric",
                  "VM"
                ],
                "quote": "今日客流 38,214，环比 +6.2%，口径=已去重闸机。",
                "time": "10:00",
                "source": "footfall",
                "conf": 99
              },
              {
                "kind": "Finding",
                "id": "EV-7704",
                "chain": [
                  "Comment",
                  "Cluster",
                  "Finding"
                ],
                "quote": "停车体验簇占负面 30.8%。",
                "time": "09:31",
                "source": "cluster.rule",
                "conf": 93
              }
            ]
          }
        ],
        "side": [
          {
            "type": "insight",
            "text": "离场高峰的停车摩擦正在抵消晚间促销带来的客流增量，建议 18–21 点增派引导并开放 B3 备用通道。",
            "why": "依据 EV-7701/7704/7710：客流升但负面同向升，时间重合度 47%。",
            "kind": "决策建议",
            "evidence": [
              "EV-7701",
              "EV-7704",
              "EV-7710"
            ],
            "actions": [
              {
                "label": "生成处置 Case",
                "variant": "secondary",
                "id": "mk-case",
                "cls": "DRAFT",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "ico": "case"
              }
            ]
          },
          {
            "type": "risks",
            "items": [
              {
                "level": "high",
                "title": "停车/离场摩擦",
                "evidence": "EV-7710",
                "desc": "晚高峰集中，风险分 72。",
                "score": 72
              },
              {
                "level": "med",
                "title": "会员复购下滑",
                "evidence": "EV-7699",
                "desc": "近 7 日复购率 -2.4pt。",
                "score": 46
              }
            ]
          },
          {
            "type": "actions",
            "title": "建议行动",
            "items": [
              {
                "id": "open-event",
                "title": "打开事件 EV-7710",
                "icon": "event",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "CTH-04",
                "permission": "UNKNOWN",
                "desc": "NAVIGATION"
              },
              {
                "id": "draft-action",
                "title": "起草引导排班调整",
                "icon": "edit",
                "cls": "NAVIGATION",
                "scope": "subject:current",
                "target": "ops_plan",
                "permission": "plan:write",
                "desc": "DRAFT"
              },
              {
                "id": "notify-team",
                "title": "通知运营值班群",
                "icon": "message",
                "cls": "NAVIGATION",
                "scope": "team:ops",
                "target": "im",
                "permission": "notify:write",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          },
          {
            "type": "runtime",
            "title": "数据新鲜度",
            "items": [
              {
                "name": "Canonical 主链",
                "state": "ok",
                "detail": "10:00 已确认"
              },
              {
                "name": "采集器 ×6",
                "state": "ok",
                "detail": "5 个运行/1 待机"
              },
              {
                "name": "AI 派生",
                "state": "idle",
                "detail": "不影响主链"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7701",
        "EV-7704",
        "EV-7706",
        "EV-7710"
      ]
    }
  },
  "CTH-02": {
    "titleKey": "screen.CTH-02",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "主体档案 / 业务单元 / 品牌业态",
        "titleKey": "screen.CTH-02",
        "desc": "选择主体只改变工作上下文；品牌、业态、业务单元的事实归属保持不变。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "cards",
            "items": [
              {
                "title": "广州太古汇",
                "desc": "商业综合体 ·  mall_group",
                "ico": "target",
                "badge": {
                  "text": "当前主体",
                  "cls": "brand"
                },
                "meta": "subject_id=subj_taikoo_hui"
              },
              {
                "title": "业务单元 12",
                "desc": "北区/西区/L1-L4 等",
                "ico": "layers"
              },
              {
                "title": "在场品牌 386",
                "desc": "零售/餐饮/体验/服务",
                "ico": "campaign"
              },
              {
                "title": "业态 24",
                "desc": "一级业态 6 / 二级 18",
                "ico": "grid"
              }
            ],
            "cols": 2
          },
          {
            "type": "table",
            "title": "品牌与业态",
            "columns": [
              {
                "label": "品牌",
                "key": "b"
              },
              {
                "label": "业态",
                "key": "cat"
              },
              {
                "label": "楼层",
                "key": "fl"
              },
              {
                "label": "业务单元",
                "key": "unit"
              },
              {
                "label": "状态",
                "key": "s",
                "numeric": true,
                "type": "t"
              },
              {
                "label": "声量",
                "key": "v",
                "numeric": true
              }
            ],
            "rows": [
              {
                "b": "Dior",
                "cat": "美妆精品",
                "fl": "L1",
                "unit": "西区",
                "s": "正常",
                "t": "success",
                "v": 1240
              },
              {
                "b": "lululemon",
                "cat": "运动生活",
                "fl": "L3",
                "unit": "北区",
                "s": "活动期",
                "t": "info",
                "v": 980
              },
              {
                "b": "新茶饮品牌 A",
                "cat": "餐饮",
                "fl": "B1",
                "unit": "食集",
                "s": "新入驻",
                "t": "warning",
                "v": 412
              },
              {
                "b": "体验品牌 B",
                "cat": "体验业态",
                "fl": "L4",
                "unit": "北区",
                "s": "装修",
                "t": "neutral",
                "v": 0
              }
            ]
          }
        ],
        "side": [
          {
            "type": "filters",
            "chips": [
              {
                "label": "全部",
                "on": true
              },
              {
                "label": "零售",
                "on": false
              },
              {
                "label": "餐饮",
                "on": false
              },
              {
                "label": "体验",
                "on": false
              },
              {
                "label": "服务",
                "on": false
              }
            ]
          },
          {
            "type": "chart",
            "title": "业态声量占比",
            "kind": "ring",
            "parts": [
              {
                "v": 34,
                "color": "var(--lum-c-brand-500)"
              },
              {
                "v": 26,
                "color": "var(--lum-c-info)"
              },
              {
                "v": 18,
                "color": "var(--lum-c-success)"
              },
              {
                "v": 22,
                "color": "var(--lum-c-slate-300)"
              }
            ]
          },
          {
            "type": "note",
            "text": "品牌/业态为业务数据（ViewModel），不进入 i18n；主体切换不重写 Canonical 归属。",
            "kind": "RULE",
            "code": "SUBJECT-CTX"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV: subject_profile",
        "EV: brand_directory"
      ]
    }
  },
  "CTH-03": {
    "titleKey": "screen.CTH-03",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "实时监测",
        "titleKey": "screen.CTH-03",
        "desc": "采集→Canonical→指标的实时链路，区分实时值与已确认值，展示采集器健康。"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "实时在线提及/分",
            "value": 86,
            "icon": "runtime",
            "source": "STREAM: collector",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "已确认延迟",
            "value": 38,
            "icon": "clock",
            "source": "RUNTIME: pipeline",
            "fresh": "live",
            "decimals": 0,
            "unit": "s"
          },
          {
            "label": "活跃采集器",
            "value": 5,
            "icon": "collector",
            "source": "RUNTIME: collector",
            "fresh": "live",
            "decimals": 0,
            "unit": "/6"
          },
          {
            "label": "待入链消息",
            "value": 12,
            "icon": "layers",
            "source": "STREAM: queue",
            "fresh": "live",
            "decimals": 0
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "实时声量流（分钟）",
            "kind": "line",
            "series": [
              {
                "data": [
                  40,
                  55,
                  51,
                  68,
                  62,
                  74,
                  70,
                  86,
                  80,
                  86
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "-9",
              "-8",
              "-7",
              "-6",
              "-5",
              "-4",
              "-3",
              "-2",
              "-1",
              "now"
            ]
          },
          {
            "type": "runtime",
            "title": "采集器",
            "items": [
              {
                "name": "小红书采集",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "微博采集",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "评论同步",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "点评采集",
                "state": "warn",
                "detail": "限流退避"
              },
              {
                "name": "会员/闸机",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "外部 API",
                "state": "idle",
                "detail": "standby"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "events",
            "title": "实时事件流",
            "items": [
              {
                "time": "now",
                "title": "新帖：停车相关",
                "desc": "小红书 · 负面倾向 0.71",
                "date": "实时",
                "level": "med",
                "tags": [
                  "停车"
                ],
                "evidence": "EV-STREAM"
              },
              {
                "time": "1m",
                "title": "微博提及 +12",
                "desc": "话题 #广州太古汇#",
                "date": "1m",
                "level": "low",
                "tags": [
                  "微博"
                ],
                "evidence": "EV-STREAM"
              }
            ],
            "more": true
          },
          {
            "type": "note",
            "text": "实时流是未确认数据，进入 Canonical 前不计入正式指标；界面用不同视觉区分 live vs confirmed。",
            "kind": "RULE",
            "code": "LIVE-VS-CONFIRMED"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "RUNTIME: collector/pipeline"
      ]
    }
  },
  "CTH-04": {
    "titleKey": "screen.CTH-04",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "事件与事件关系",
        "titleKey": "screen.CTH-04",
        "desc": "Source→Event→Case 的关系图与时间线，点击节点回跳证据。",
        "actions": [
          {
            "label": "新建事件",
            "variant": "primary",
            "id": "new-event",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "event:write",
            "ico": "plus"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "raw",
            "html": "<section class=\"lum-card lum-card-pad\" data-reveal><div class=\"lum-section-head\"><span class=\"lum-eyebrow\">Event Graph</span><h3 class=\"lum-h4\">事件关系图（原型示意）</h3></div>\n      <svg viewBox=\"0 0 560 300\" class=\"lum-chart\" role=\"img\" aria-label=\"event graph\">\n        <line x1=\"120\" y1=\"80\" x2=\"300\" y2=\"150\" class=\"lum-flow-link\"/>\n        <line x1=\"120\" y1=\"220\" x2=\"300\" y2=\"150\" class=\"lum-flow-link\"/>\n        <line x1=\"300\" y1=\"150\" x2=\"470\" y2=\"90\" class=\"lum-flow-link\"/>\n        <line x1=\"300\" y1=\"150\" x2=\"470\" y2=\"210\" class=\"lum-flow-link\"/>\n        <g><circle cx=\"120\" cy=\"80\" r=\"34\" fill=\"var(--lum-c-brand-100)\"/><text x=\"120\" y=\"84\" text-anchor=\"middle\" font-size=\"11\" fill=\"var(--lum-text)\">评论簇</text></g>\n        <g><circle cx=\"120\" cy=\"220\" r=\"34\" fill=\"var(--lum-c-warning-bg)\"/><text x=\"120\" y=\"224\" text-anchor=\"middle\" font-size=\"11\" fill=\"var(--lum-text)\">帖子簇</text></g>\n        <g><circle cx=\"300\" cy=\"150\" r=\"42\" fill=\"var(--lum-c-brand-500)\"/><text x=\"300\" y=\"154\" text-anchor=\"middle\" font-size=\"11\" fill=\"var(--lum-text-invert)\">EV-7710</text></g>\n        <g><circle cx=\"470\" cy=\"90\" r=\"32\" fill=\"var(--lum-c-danger-bg)\"/><text x=\"470\" y=\"94\" text-anchor=\"middle\" font-size=\"11\" fill=\"var(--lum-text)\">Case</text></g>\n        <g><circle cx=\"470\" cy=\"210\" r=\"32\" fill=\"var(--lum-c-info-bg)\"/><text x=\"470\" y=\"214\" text-anchor=\"middle\" font-size=\"11\" fill=\"var(--lum-text)\">Risk</text></g>\n      </svg></section>"
          },
          {
            "type": "events",
            "title": "事件时间线",
            "items": [
              {
                "time": "09:05",
                "title": "首条相关评论",
                "desc": "",
                "date": "09-10",
                "level": "low",
                "tags": [],
                "evidence": "EV-7690"
              },
              {
                "time": "09:31",
                "title": "聚类形成停车簇",
                "desc": "96 条",
                "date": "09-10",
                "level": "med",
                "tags": [],
                "evidence": "EV-7704"
              },
              {
                "time": "10:22",
                "title": "升级为事件 EV-7710",
                "desc": "风险分 72",
                "date": "09-10",
                "level": "high",
                "tags": [],
                "evidence": "EV-7710"
              }
            ],
            "more": true
          }
        ],
        "side": [
          {
            "type": "evidence",
            "title": "事件证据",
            "items": [
              {
                "kind": "Event",
                "id": "EV-7710",
                "chain": [
                  "Cluster",
                  "Event",
                  "Case?",
                  "Risk?"
                ],
                "quote": "停车/离场摩擦事件，关联 3 个簇、2 个潜在 Case。",
                "time": "10:22",
                "source": "event_engine",
                "conf": 91
              }
            ]
          },
          {
            "type": "actions",
            "title": "事件操作",
            "items": [
              {
                "id": "to-case",
                "title": "转 Case",
                "icon": "case",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "case:write",
                "desc": "DRAFT"
              },
              {
                "id": "link-risk",
                "title": "关联风险",
                "icon": "risk",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "DRAFT"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7710",
        "EV: event_graph"
      ]
    }
  },
  "CTH-05": {
    "titleKey": "screen.CTH-05",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "舆情日历",
        "titleKey": "screen.CTH-05",
        "desc": "按日聚合情绪/事件密度，点选日期联动右侧证据与事件。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "raw",
            "html": "<section class=\"lum-card lum-card-pad\" data-reveal><div class=\"lum-section-head\"><span class=\"lum-eyebrow\">Calendar</span><h3 class=\"lum-h4\">2026 年 9 月</h3></div>\n      <div style=\"display:grid;grid-template-columns:repeat(7,1fr);gap:8px\" id=\"cal-grid\"></div></section>"
          }
        ],
        "side": [
          {
            "type": "events",
            "title": "当日明细 · 09-10",
            "items": [
              {
                "time": "10:22",
                "title": "停车事件升级",
                "desc": "",
                "date": "",
                "level": "high",
                "tags": [],
                "evidence": "EV-7710"
              },
              {
                "time": "09:05",
                "title": "快闪开业",
                "desc": "",
                "date": "",
                "level": "low",
                "tags": [],
                "evidence": "EV-7706"
              }
            ],
            "more": true
          },
          {
            "type": "kpis",
            "items": [
              {
                "label": "当日负面",
                "value": 12,
                "icon": "risk",
                "source": "EV:calendar",
                "fresh": "live",
                "decimals": 0
              },
              {
                "label": "当日事件",
                "value": 3,
                "icon": "event",
                "source": "EV:calendar",
                "fresh": "live",
                "decimals": 0
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV: calendar aggregate"
      ]
    },
    "onMountClient": "fillCalendar"
  },
  "CTH-06": {
    "titleKey": "screen.CTH-06",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "负面监测与用户/评论反馈",
        "titleKey": "screen.CTH-06",
        "desc": "负面条目必须可追溯到原始 Source；区分用户反馈与公开舆情。"
      },
      {
        "type": "filters",
        "chips": [
          {
            "label": "全部",
            "on": true
          },
          {
            "label": "公开舆情",
            "on": false
          },
          {
            "label": "用户反馈",
            "on": false
          },
          {
            "label": "评论",
            "on": false
          },
          {
            "label": "高风险",
            "on": false
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "table",
            "title": "负面条目",
            "columns": [
              {
                "label": "时间",
                "key": "t"
              },
              {
                "label": "渠道",
                "key": "ch"
              },
              {
                "label": "内容摘要",
                "key": "c"
              },
              {
                "label": "情绪",
                "key": "s",
                "numeric": true,
                "type": "st"
              },
              {
                "label": "簇",
                "key": "clu"
              },
              {
                "label": "证据",
                "key": "ev"
              }
            ],
            "rows": [
              {
                "t": "10:21",
                "ch": "小红书",
                "c": "B3 找车绕了二十分钟……",
                "s": "负面",
                "st": "danger",
                "clu": "停车",
                "ev": "EV-7720"
              },
              {
                "t": "09:58",
                "ch": "会员反馈",
                "c": "北区指引牌不够明显",
                "s": "负面",
                "st": "warning",
                "clu": "指引",
                "ev": "EV-7721"
              },
              {
                "t": "09:40",
                "ch": "微博",
                "c": "晚高峰排队但活动不错",
                "s": "中性",
                "st": "neutral",
                "clu": "活动",
                "ev": "EV-7722"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "risks",
            "items": [
              {
                "level": "high",
                "title": "停车体验",
                "evidence": "EV-7704",
                "desc": "96 条/30.8%",
                "score": 72
              },
              {
                "level": "med",
                "title": "指引不清",
                "evidence": "EV-7712",
                "score": 48
              }
            ]
          },
          {
            "type": "evidence",
            "title": "原始来源",
            "items": [
              {
                "kind": "Source",
                "id": "EV-7720",
                "chain": [
                  "Source",
                  "Comment"
                ],
                "quote": "原帖快照与链接已固定，采集时间 10:21。",
                "time": "10:21",
                "source": "xhs",
                "conf": 97
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7704",
        "EV-7720"
      ]
    }
  },
  "CTH-07": {
    "titleKey": "screen.CTH-07",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "趋势分析",
        "titleKey": "screen.CTH-07",
        "desc": "统一口径下的多指标趋势、同环比与构成变化，所有数值来自 Canonical。"
      },
      {
        "type": "filters",
        "chips": [
          {
            "label": "近 7 天",
            "on": false
          },
          {
            "label": "近 30 天",
            "on": true
          },
          {
            "label": "近 90 天",
            "on": false
          },
          {
            "label": "自定义",
            "on": false
          }
        ]
      },
      {
        "type": "chart",
        "title": "客流 / 销售 / 声量趋势",
        "kind": "line",
        "series": [
          {
            "data": [
              60,
              66,
              64,
              72,
              78,
              76,
              84
            ],
            "color": "var(--lum-c-brand-500)"
          },
          {
            "data": [
              42,
              46,
              45,
              50,
              55,
              54,
              60
            ],
            "color": "var(--lum-c-success)"
          },
          {
            "data": [
              30,
              34,
              33,
              41,
              44,
              42,
              49
            ],
            "color": "var(--lum-c-warning)"
          }
        ],
        "labels": [
          "9/2",
          "9/5",
          "9/8",
          "9/11",
          "9/14",
          "9/17",
          "9/20"
        ],
        "legend": [
          {
            "label": "客流",
            "color": "var(--lum-c-brand-500)"
          },
          {
            "label": "销售",
            "color": "var(--lum-c-success)"
          },
          {
            "label": "声量",
            "color": "var(--lum-c-warning)"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "负面构成变化",
            "kind": "bar",
            "series": [
              {
                "data": [
                  30,
                  18,
                  16,
                  14,
                  22
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "停车",
              "指引",
              "排队",
              "价格",
              "其他"
            ]
          },
          {
            "type": "insight",
            "text": "停车类占比连续 3 日上升，与晚高峰客流高度相关，是本周主要拖累项。",
            "why": "构成变化 + 时间重合度，见 EV-7704/7710。",
            "evidence": [
              "EV-7704",
              "EV-7710"
            ]
          }
        ],
        "side": []
      }
    ],
    "context": {
      "evidence": [
        "EV: canonical_metrics"
      ]
    }
  },
  "CTH-08": {
    "titleKey": "screen.CTH-08",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "案例库 / 案例分析 / 知识库",
        "titleKey": "screen.CTH-08",
        "desc": "Case 由事件与证据沉淀，知识库沉淀可复用结论，不覆盖原始事实。",
        "actions": [
          {
            "label": "新建案例",
            "variant": "primary",
            "id": "new-case",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "case:write",
            "ico": "case"
          }
        ]
      },
      {
        "type": "tabs",
        "id": "cth08",
        "tabs": [
          {
            "label": "案例库",
            "sections": [
              {
                "type": "table",
                "title": "",
                "columns": [
                  {
                    "label": "案例",
                    "key": "n"
                  },
                  {
                    "label": "状态",
                    "key": "s",
                    "numeric": true,
                    "type": "t"
                  },
                  {
                    "label": "关联事件",
                    "key": "e"
                  },
                  {
                    "label": "风险",
                    "key": "r"
                  },
                  {
                    "label": "证据",
                    "key": "ev"
                  }
                ],
                "rows": [
                  {
                    "n": "晚高峰停车摩擦处置",
                    "s": "进行中",
                    "t": "warning",
                    "e": "EV-7710",
                    "r": "高",
                    "ev": "CASE-221"
                  },
                  {
                    "n": "快闪开业保障",
                    "s": "已关闭",
                    "t": "success",
                    "e": "EV-7706",
                    "r": "低",
                    "ev": "CASE-218"
                  },
                  {
                    "n": "会员日复盘",
                    "s": "已归档",
                    "t": "neutral",
                    "e": "EV-7688",
                    "r": "低",
                    "ev": "CASE-210"
                  }
                ]
              }
            ]
          },
          {
            "label": "案例分析",
            "sections": [
              {
                "type": "evidence",
                "title": "案例证据链",
                "items": [
                  {
                    "kind": "Case",
                    "id": "CASE-221",
                    "chain": [
                      "Event",
                      "Evidence",
                      "Decision",
                      "Action",
                      "Outcome"
                    ],
                    "quote": "处置：增派引导+开放 B3，平均离场时间 -6.2 分钟。",
                    "time": "进行中",
                    "source": "case_engine",
                    "conf": 90
                  }
                ]
              },
              {
                "type": "timeline",
                "title": "处置时间线",
                "items": [
                  {
                    "time": "10:22",
                    "title": "建 Case",
                    "desc": null,
                    "done": true
                  },
                  {
                    "time": "10:40",
                    "title": "指派运营",
                    "desc": null,
                    "done": true
                  },
                  {
                    "time": "11:00",
                    "title": "现场执行",
                    "desc": "观察中",
                    "done": false
                  }
                ],
                "label": null
              }
            ]
          },
          {
            "label": "知识库",
            "sections": [
              {
                "type": "cards",
                "items": [
                  {
                    "title": "高峰停车疏导 SOP",
                    "desc": "历史复盘沉淀的标准动作",
                    "ico": "folder",
                    "badge": {
                      "text": "可复用",
                      "cls": "brand"
                    }
                  },
                  {
                    "title": "快闪活动保障清单",
                    "desc": "跨部门 checklist",
                    "ico": "folder"
                  },
                  {
                    "title": "负面回应口径模板",
                    "desc": "经审批的回应模板",
                    "ico": "content"
                  }
                ],
                "cols": 3
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "CASE-221",
        "EV-7710"
      ]
    }
  },
  "CTH-09": {
    "titleKey": "screen.CTH-09",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "风险中心与决策看板",
        "titleKey": "screen.CTH-09",
        "desc": "风险分、决策项、行动与证据一屏对齐；高风险行动需确认与权限。"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "严重风险",
            "value": 1,
            "icon": "risk",
            "source": "EV:risk",
            "fresh": "live",
            "decimals": 0,
            "delta": 0,
            "deltaUnit": ""
          },
          {
            "label": "高风险",
            "value": 3,
            "icon": "alert",
            "source": "EV:risk",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "待决策",
            "value": 5,
            "icon": "target",
            "source": "EV:decision",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "已缓解(7d)",
            "value": 11,
            "icon": "check",
            "source": "EV:risk",
            "fresh": "live",
            "decimals": 0
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "risks",
            "items": [
              {
                "level": "critical",
                "title": "晚高峰停车摩擦",
                "evidence": "EV-7710",
                "desc": "影响到店体验与口碑，风险分 84。",
                "score": 84
              },
              {
                "level": "high",
                "title": "会员复购下滑",
                "evidence": "EV-7699",
                "desc": "复购率 -2.4pt，需运营干预。",
                "score": 68
              },
              {
                "level": "med",
                "title": "北区指引不清",
                "evidence": "EV-7712",
                "desc": "投诉占 18%。",
                "score": 48
              },
              {
                "level": "low",
                "title": "活动物料库存偏紧",
                "evidence": "EV-7715",
                "desc": "预计 3 天后到安全线。",
                "score": 26
              }
            ]
          }
        ],
        "side": [
          {
            "type": "actions",
            "title": "待决策",
            "items": [
              {
                "id": "decide-b3",
                "title": "开放 B3 备用通道（18-21点）",
                "icon": "check",
                "cls": "NAVIGATION",
                "scope": "facility:parking",
                "target": "access_control",
                "permission": "facility:write",
                "desc": "EFFECT",
                "risk": true
              },
              {
                "id": "decide-staff",
                "title": "增派晚高峰引导 4 人",
                "icon": "users",
                "cls": "NAVIGATION",
                "scope": "team:ops",
                "target": "roster",
                "permission": "roster:write",
                "desc": "DRAFT"
              },
              {
                "id": "decide-sign",
                "title": "更新北区指引标识",
                "icon": "edit",
                "cls": "NAVIGATION",
                "scope": "facility:signage",
                "target": "work_order",
                "permission": "ops:write",
                "desc": "DRAFT"
              }
            ]
          },
          {
            "type": "evidence",
            "title": "决策依据",
            "items": [
              {
                "kind": "Risk",
                "id": "EV-7710",
                "chain": [
                  "Metric",
                  "Cluster",
                  "Risk",
                  "Decision"
                ],
                "quote": "风险分 84，依据 312 条评论与现场记录。",
                "time": "10:22",
                "source": "risk_engine",
                "conf": 90
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7710",
        "EV-7699",
        "EV-7712"
      ]
    }
  },
  "CTH-10": {
    "titleKey": "screen.CTH-10",
    "sections": [
      {
        "type": "head",
        "eyebrow": "CTH · 商业运营",
        "title": "报告 / 周报 / 证据",
        "titleKey": "screen.CTH-10",
        "desc": "报告由 Canonical 与 Evidence 生成，导出保留口径、时间窗与证据清单。",
        "actions": [
          {
            "label": "生成周报",
            "variant": "primary",
            "id": "gen-weekly",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "report:write",
            "ico": "report"
          },
          {
            "label": "导出 PDF/Excel",
            "variant": "secondary",
            "id": "export",
            "cls": "QUERY",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "download"
          }
        ]
      },
      {
        "type": "tabs",
        "id": "cth10",
        "tabs": [
          {
            "label": "报告列表",
            "sections": [
              {
                "type": "table",
                "title": "",
                "columns": [
                  {
                    "label": "报告",
                    "key": "n"
                  },
                  {
                    "label": "周期",
                    "key": "p"
                  },
                  {
                    "label": "状态",
                    "key": "s",
                    "numeric": true,
                    "type": "t"
                  },
                  {
                    "label": "证据数",
                    "key": "e",
                    "numeric": true
                  },
                  {
                    "label": "更新",
                    "key": "u"
                  }
                ],
                "rows": [
                  {
                    "n": "商业运营周报 W37",
                    "p": "09/02-09/08",
                    "s": "已确认",
                    "t": "success",
                    "e": 128,
                    "u": "09-09"
                  },
                  {
                    "n": "停车专题分析",
                    "p": "近30天",
                    "s": "草稿",
                    "t": "warning",
                    "e": 42,
                    "u": "10:20"
                  },
                  {
                    "n": "会员日 Campaign 复盘",
                    "p": "活动期",
                    "s": "已归档",
                    "t": "neutral",
                    "e": 96,
                    "u": "09-05"
                  }
                ]
              }
            ]
          },
          {
            "label": "周报预览",
            "sections": [
              {
                "type": "insight",
                "text": "本周客流 +6.2%、销售占比 +2.1pt；停车摩擦为主要风险，建议晚高峰增派引导并开放 B3。",
                "evidence": [
                  "EV-7701",
                  "EV-7710"
                ]
              },
              {
                "type": "chart",
                "title": "周内关键指标",
                "kind": "bar",
                "series": [
                  {
                    "data": [
                      62,
                      71,
                      78,
                      70,
                      84,
                      90,
                      88
                    ],
                    "color": "var(--lum-c-brand-500)"
                  }
                ],
                "labels": [
                  "一",
                  "二",
                  "三",
                  "四",
                  "五",
                  "六",
                  "日"
                ]
              }
            ]
          },
          {
            "label": "证据清单",
            "sections": [
              {
                "type": "evidence",
                "title": "报告引用证据",
                "items": [
                  {
                    "kind": "Metric",
                    "id": "EV-7701",
                    "chain": [
                      "Source",
                      "Canonical",
                      "Metric",
                      "Report"
                    ],
                    "quote": "客流口径与数值。",
                    "time": "09-09",
                    "source": "canonical",
                    "conf": 99
                  },
                  {
                    "kind": "Risk",
                    "id": "EV-7710",
                    "chain": [
                      "Risk",
                      "Report"
                    ],
                    "quote": "风险分与依据。",
                    "time": "09-09",
                    "source": "risk_engine",
                    "conf": 90
                  }
                ]
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "报告内全部 EV 清单随导出固化"
      ]
    }
  },
  "BMP-01": {
    "titleKey": "screen.BMP-01",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 序境·品牌市场",
        "title": "品牌市场总览",
        "titleKey": "screen.BMP-01",
        "desc": "品牌健康、传播、创作者与市场情报的统一视图，全部锚定证据。",
        "actions": [
          {
            "label": "品牌简报",
            "variant": "primary",
            "id": "draft",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "report:write",
            "ico": "report"
          },
          {
            "label": "切换品牌",
            "variant": "secondary",
            "id": "",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "campaign"
          }
        ]
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "品牌健康分",
            "value": 82.4,
            "icon": "evaluation",
            "source": "EV:brand_health",
            "fresh": "live",
            "decimals": 1,
            "delta": 1.6,
            "deltaUnit": "%",
            "spark": [
              12,
              18,
              15,
              22,
              19,
              26,
              24
            ]
          },
          {
            "label": "全网声量",
            "value": 28640,
            "icon": "trend",
            "source": "EV:voice.canonical",
            "fresh": "live",
            "decimals": 0,
            "delta": 9.4,
            "deltaUnit": "%",
            "spark": [
              8,
              10,
              9,
              13,
              12,
              15,
              14,
              18,
              16,
              20,
              19,
              22
            ]
          },
          {
            "label": "正向占比",
            "value": 76.2,
            "icon": "check",
            "source": "EV:sentiment",
            "fresh": "live",
            "decimals": 1,
            "unit": "%",
            "delta": 2.0,
            "deltaUnit": "%",
            "spark": [
              20,
              17,
              22,
              19,
              25,
              21,
              28
            ]
          },
          {
            "label": "在投 Campaign",
            "value": 4,
            "icon": "campaign",
            "source": "EV:campaign.open",
            "fresh": "live",
            "decimals": 0
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "声量与情绪趋势",
            "kind": "line",
            "series": [
              {
                "data": [
                  40,
                  48,
                  46,
                  55,
                  60,
                  58,
                  66
                ],
                "color": "var(--lum-c-brand-500)"
              },
              {
                "data": [
                  28,
                  30,
                  33,
                  32,
                  38,
                  37,
                  42
                ],
                "color": "var(--lum-c-success)"
              }
            ],
            "labels": [
              "9/2",
              "9/5",
              "9/8",
              "9/11",
              "9/14",
              "9/17",
              "9/20"
            ],
            "legend": [
              {
                "label": "声量",
                "color": "var(--lum-c-brand-500)"
              },
              {
                "label": "正向",
                "color": "var(--lum-c-success)"
              }
            ]
          },
          {
            "type": "events",
            "title": "品牌动态",
            "items": [
              {
                "time": "09:40",
                "title": "新品话题进入热榜",
                "desc": "微博话题榜 #36",
                "date": "09-10",
                "level": "low",
                "tags": [
                  "传播"
                ],
                "evidence": "EV-B110"
              },
              {
                "time": "昨日",
                "title": "竞品发布同类新品",
                "desc": "声量 +44%",
                "date": "09-09",
                "level": "med",
                "tags": [
                  "竞品"
                ],
                "evidence": "EV-B108"
              }
            ],
            "more": true
          }
        ],
        "side": [
          {
            "type": "insight",
            "text": "正向占比回升主要来自 KOC 真实体验内容；建议把预算向腰部 KOC 倾斜并复用高互动脚本。",
            "why": "创作者分层贡献拆解，见 EV-B110/B112。",
            "evidence": [
              "EV-B110",
              "EV-B112"
            ]
          },
          {
            "type": "risks",
            "items": [
              {
                "level": "med",
                "title": "竞品声量反超",
                "evidence": "EV-B108",
                "desc": "同类新品窗口，需 72h 内回应。",
                "score": 52
              }
            ]
          },
          {
            "type": "actions",
            "title": "建议行动",
            "items": [
              {
                "id": "go-creator",
                "title": "打开创作者分析",
                "icon": "creators",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "BMP-05",
                "permission": "UNKNOWN",
                "desc": "NAVIGATION"
              },
              {
                "id": "draft-plan",
                "title": "起草传播计划",
                "icon": "edit",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "plan:write",
                "desc": "DRAFT"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-B108",
        "EV-B110",
        "EV-B112"
      ]
    }
  },
  "BMP-02": {
    "titleKey": "screen.BMP-02",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "品牌中心 / 多品牌与竞品",
        "titleKey": "screen.BMP-02",
        "desc": "管理自有多品牌与竞品集合，切换品牌即切换 Subject 上下文。"
      },
      {
        "type": "filters",
        "chips": [
          {
            "label": "自有品牌",
            "on": true
          },
          {
            "label": "竞品",
            "on": false
          },
          {
            "label": "全部",
            "on": false
          }
        ]
      },
      {
        "type": "cards",
        "items": [
          {
            "title": "主品牌",
            "desc": "健康分 82.4 · 声量 28.6k",
            "ico": "campaign",
            "badge": {
              "text": "当前",
              "cls": "brand"
            }
          },
          {
            "title": "子品牌 A",
            "desc": "健康分 76.1",
            "ico": "campaign"
          },
          {
            "title": "竞品 X",
            "desc": "声量反超，重点跟踪",
            "ico": "target",
            "badge": {
              "text": "竞品",
              "cls": "warning"
            }
          },
          {
            "title": "竞品 Y",
            "desc": "稳态",
            "ico": "target",
            "badge": {
              "text": "竞品",
              "cls": "neutral"
            }
          }
        ],
        "cols": 4
      },
      {
        "type": "table",
        "title": "品牌对比（同口径）",
        "columns": [
          {
            "label": "品牌",
            "key": "b"
          },
          {
            "label": "健康分",
            "key": "h",
            "numeric": true
          },
          {
            "label": "声量",
            "key": "v",
            "numeric": true
          },
          {
            "label": "正向%",
            "key": "p",
            "numeric": true
          },
          {
            "label": "互动率",
            "key": "i",
            "numeric": true
          },
          {
            "label": "证据",
            "key": "ev"
          }
        ],
        "rows": [
          {
            "b": "主品牌",
            "h": 82.4,
            "v": 28640,
            "p": 76.2,
            "i": 4.8,
            "ev": "EV-B201"
          },
          {
            "b": "子品牌 A",
            "h": 76.1,
            "v": 12040,
            "p": 71.0,
            "i": 3.9,
            "ev": "EV-B202"
          },
          {
            "b": "竞品 X",
            "h": 79.8,
            "v": 31200,
            "p": 73.4,
            "i": 5.2,
            "ev": "EV-B203"
          },
          {
            "b": "竞品 Y",
            "h": 70.2,
            "v": 9020,
            "p": 68.1,
            "i": 3.1,
            "ev": "EV-B204"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-B201..204"
      ]
    }
  },
  "BMP-03": {
    "titleKey": "screen.BMP-03",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "市场情报",
        "titleKey": "screen.BMP-03",
        "desc": "行业趋势、品类机会与外部情报，区分已确认情报与待核实线索。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "品类热度走势",
            "kind": "line",
            "series": [
              {
                "data": [
                  30,
                  34,
                  38,
                  36,
                  44,
                  48,
                  52
                ],
                "color": "var(--lum-c-info)"
              }
            ],
            "labels": [
              "9/2",
              "9/5",
              "9/8",
              "9/11",
              "9/14",
              "9/17",
              "9/20"
            ]
          },
          {
            "type": "cards",
            "items": [
              {
                "title": "品类机会：体验业态",
                "desc": "搜索热度 +22%，竞品布局不足",
                "ico": "research",
                "badge": {
                  "text": "机会",
                  "cls": "success"
                }
              },
              {
                "title": "渠道迁移",
                "desc": "短视频→直播转化提升",
                "ico": "research"
              },
              {
                "title": "政策/合规提示",
                "desc": "广告法敏感词更新",
                "ico": "security",
                "badge": {
                  "text": "合规",
                  "cls": "warning"
                }
              }
            ],
            "cols": 1
          }
        ],
        "side": [
          {
            "type": "evidence",
            "title": "情报来源",
            "items": [
              {
                "kind": "External",
                "id": "EV-B301",
                "chain": [
                  "External",
                  "Intel",
                  "VM"
                ],
                "quote": "行业报告：体验业态 Q3 增速领先。",
                "time": "09-08",
                "source": "market.report",
                "conf": 82
              },
              {
                "kind": "Social",
                "id": "EV-B302",
                "chain": [
                  "Social",
                  "Intel"
                ],
                "quote": "话题聚类显示「场景化体验」上升。",
                "time": "09-09",
                "source": "social.cluster",
                "conf": 78
              }
            ]
          },
          {
            "type": "note",
            "text": "外部情报置信度低于内部 Canonical，界面分级展示并要求二次核实后才进入决策。",
            "kind": "RULE",
            "code": "INTEL-CONF"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-B301",
        "EV-B302"
      ]
    }
  },
  "BMP-04": {
    "titleKey": "screen.BMP-04",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "传播分析",
        "titleKey": "screen.BMP-04",
        "desc": "渠道×内容×时段的传播表现与转化漏斗，统一口径。"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "总曝光",
            "value": 1.28,
            "icon": "trend",
            "source": "EV:reach",
            "fresh": "live",
            "decimals": 2,
            "unit": "M",
            "delta": 11,
            "deltaUnit": "%"
          },
          {
            "label": "互动率",
            "value": 4.8,
            "icon": "creators",
            "source": "EV:engage",
            "fresh": "live",
            "decimals": 1,
            "unit": "%"
          },
          {
            "label": "转发/收藏",
            "value": 38420,
            "icon": "share",
            "source": "EV:share",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "引流转化",
            "value": 2.1,
            "icon": "arrow-right",
            "source": "EV:convert",
            "fresh": "live",
            "decimals": 1,
            "unit": "%"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "渠道贡献",
            "kind": "bar",
            "series": [
              {
                "data": [
                  42,
                  28,
                  16,
                  9,
                  5
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "小红书",
              "抖音",
              "微博",
              "微信",
              "其他"
            ]
          },
          {
            "type": "chart",
            "title": "传播漏斗",
            "kind": "bar",
            "series": [
              {
                "data": [
                  100,
                  64,
                  38,
                  18,
                  9
                ],
                "color": "var(--lum-c-info)"
              }
            ],
            "labels": [
              "曝光",
              "点击",
              "互动",
              "加购",
              "转化"
            ]
          }
        ],
        "side": [
          {
            "type": "insight",
            "text": "小红书贡献最高互动但转化偏低，抖音引流转化更优，建议组合投放并 A/B 脚本。",
            "evidence": [
              "EV-B401",
              "EV-B402"
            ]
          },
          {
            "type": "evidence",
            "title": "口径",
            "items": [
              {
                "kind": "Metric",
                "id": "EV-B401",
                "chain": [
                  "Source",
                  "Canonical",
                  "Metric"
                ],
                "quote": "渠道去重口径，已排除刷量异常。",
                "time": "09-09",
                "source": "canonical",
                "conf": 95
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-B401",
        "EV-B402"
      ]
    }
  },
  "BMP-05": {
    "titleKey": "screen.BMP-05",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "创作者 KOS / KOL / KOC / UGC",
        "titleKey": "screen.BMP-05",
        "desc": "分层管理创作者，评估真实贡献与合作风险，沉淀可复用脚本。",
        "actions": [
          {
            "label": "添加创作者",
            "variant": "primary",
            "id": "add",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "creator:write",
            "ico": "creators"
          }
        ]
      },
      {
        "type": "filters",
        "chips": [
          {
            "label": "全部",
            "on": true
          },
          {
            "label": "KOS",
            "on": false
          },
          {
            "label": "KOL",
            "on": false
          },
          {
            "label": "KOC",
            "on": false
          },
          {
            "label": "UGC",
            "on": false
          },
          {
            "label": "高风险",
            "on": false
          }
        ]
      },
      {
        "type": "table",
        "title": "创作者表现",
        "columns": [
          {
            "label": "创作者",
            "key": "n"
          },
          {
            "label": "分层",
            "key": "t"
          },
          {
            "label": "平台",
            "key": "p"
          },
          {
            "label": "内容数",
            "key": "c",
            "numeric": true
          },
          {
            "label": "互动率",
            "key": "i",
            "numeric": true
          },
          {
            "label": "转化",
            "key": "cv",
            "numeric": true
          },
          {
            "label": "风险",
            "key": "r",
            "numeric": true,
            "type": "rt"
          },
          {
            "label": "证据",
            "key": "ev"
          }
        ],
        "rows": [
          {
            "n": "@城市生活家",
            "t": "KOL",
            "p": "小红书",
            "c": 18,
            "i": 6.8,
            "cv": 3.2,
            "r": "低",
            "rt": "success",
            "ev": "EV-C01"
          },
          {
            "n": "门店导购·小林",
            "t": "KOS",
            "p": "抖音",
            "c": 42,
            "i": 4.1,
            "cv": 5.6,
            "r": "低",
            "rt": "success",
            "ev": "EV-C02"
          },
          {
            "n": "@真实测评君",
            "t": "KOC",
            "p": "小红书",
            "c": 9,
            "i": 9.2,
            "cv": 2.1,
            "r": "中",
            "rt": "warning",
            "ev": "EV-C03"
          },
          {
            "n": "匿名 UGC ×128",
            "t": "UGC",
            "p": "多平台",
            "c": 128,
            "i": 2.4,
            "cv": 0.8,
            "r": "待核",
            "rt": "neutral",
            "ev": "EV-C04"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "分层贡献",
            "kind": "ring",
            "parts": [
              {
                "v": 38,
                "color": "var(--lum-c-brand-500)"
              },
              {
                "v": 27,
                "color": "var(--lum-c-info)"
              },
              {
                "v": 24,
                "color": "var(--lum-c-success)"
              },
              {
                "v": 11,
                "color": "var(--lum-slate-300)"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "risks",
            "items": [
              {
                "level": "med",
                "title": "刷量嫌疑创作者 2",
                "evidence": "EV-C05",
                "desc": "互动异常，合作前需核验。",
                "score": 44
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-C01..05"
      ]
    }
  },
  "BMP-06": {
    "titleKey": "screen.BMP-06",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "内容中心",
        "titleKey": "screen.BMP-06",
        "desc": "素材/脚本/成片的生产流水线与审批状态，EFFECT 发布需权限。",
        "actions": [
          {
            "label": "新建内容",
            "variant": "primary",
            "id": "new",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "content:draft",
            "ico": "content"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "upload",
            "title": "上传素材",
            "files": [
              {
                "name": "主视觉_v3.png",
                "pct": 100,
                "stage": "已入库 · EV-M01"
              },
              {
                "name": "门店短视频.mp4",
                "pct": 64,
                "stage": "AI 分析中…"
              },
              {
                "name": "KOC 脚本包.docx",
                "pct": 18,
                "stage": "等待上传"
              }
            ],
            "dropTitle": "拖拽或点击上传素材",
            "dropHint": "支持图片/视频/文档，自动去重并建立证据"
          },
          {
            "type": "table",
            "title": "内容资产",
            "columns": [
              {
                "label": "标题",
                "key": "t"
              },
              {
                "label": "类型",
                "key": "k"
              },
              {
                "label": "状态",
                "key": "s",
                "numeric": true,
                "type": "st"
              },
              {
                "label": "审批",
                "key": "a"
              },
              {
                "label": "证据",
                "key": "ev"
              }
            ],
            "rows": [
              {
                "t": "新品体验脚本 A",
                "k": "脚本",
                "s": "草稿",
                "st": "warning",
                "a": "待提交",
                "ev": "EV-M11"
              },
              {
                "t": "门店探店成片",
                "k": "视频",
                "s": "待审批",
                "st": "info",
                "a": "审批中",
                "ev": "EV-M12"
              },
              {
                "t": "主视觉 KV",
                "k": "图片",
                "s": "已确认",
                "st": "success",
                "a": "通过",
                "ev": "EV-M01"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "actions",
            "title": "发布动作（需权限）",
            "items": [
              {
                "id": "submit-review",
                "title": "提交审批",
                "icon": "check",
                "cls": "NAVIGATION",
                "scope": "content:self",
                "target": "approval",
                "permission": "content:submit",
                "desc": "DRAFT"
              },
              {
                "id": "publish",
                "title": "发布到平台",
                "icon": "share",
                "cls": "NAVIGATION",
                "scope": "channel:external",
                "target": "publisher",
                "permission": "content:publish",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          },
          {
            "type": "note",
            "text": "内容生成是 DRAFT，必须经审批与权限校验后才能 EFFECT 发布；原型不真实发布。",
            "kind": "RULE",
            "code": "DRAFT-TO-EFFECT"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-M01",
        "EV-M11",
        "EV-M12"
      ]
    }
  },
  "BMP-07": {
    "titleKey": "screen.BMP-07",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "话题活动 Campaign",
        "titleKey": "screen.BMP-07",
        "desc": "Campaign 目标、节奏、内容与效果，按阶段推进并保留证据。"
      },
      {
        "type": "steps",
        "items": [
          {
            "label": "立项",
            "state": "is-done"
          },
          {
            "label": "内容筹备",
            "state": "is-done"
          },
          {
            "label": "投放执行",
            "state": "is-active"
          },
          {
            "label": "效果复盘",
            "state": null
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "kpis",
            "items": [
              {
                "label": "Campaign 曝光",
                "value": 640,
                "icon": "trend",
                "source": "EV:camp",
                "fresh": "live",
                "decimals": 0,
                "unit": "k",
                "delta": 14,
                "deltaUnit": "%"
              },
              {
                "label": "参与量",
                "value": 28.4,
                "icon": "creators",
                "source": "EV:camp",
                "fresh": "live",
                "decimals": 0,
                "unit": "k"
              },
              {
                "label": "话题排名",
                "value": 36,
                "icon": "trend",
                "source": "EV:camp",
                "fresh": "live",
                "decimals": 0
              },
              {
                "label": "ROI",
                "value": 4.2,
                "icon": "evaluation",
                "source": "EV:camp",
                "fresh": "live",
                "decimals": 1,
                "unit": "x"
              }
            ]
          },
          {
            "type": "chart",
            "title": "活动节奏与声量",
            "kind": "line",
            "series": [
              {
                "data": [
                  10,
                  18,
                  26,
                  40,
                  52,
                  48,
                  44
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "D1",
              "D2",
              "D3",
              "D4",
              "D5",
              "D6",
              "D7"
            ]
          }
        ],
        "side": [
          {
            "type": "timeline",
            "title": "关键节点",
            "items": [
              {
                "time": "D1",
                "title": "话题上线",
                "desc": null,
                "done": true
              },
              {
                "time": "D3",
                "title": "KOL 集中发布",
                "desc": null,
                "done": true
              },
              {
                "time": "D5",
                "title": "进入热榜",
                "desc": null,
                "done": true
              },
              {
                "time": "D7",
                "title": "复盘",
                "desc": null,
                "done": false
              }
            ],
            "label": null
          },
          {
            "type": "actions",
            "title": "活动操作",
            "items": [
              {
                "id": "add-content",
                "title": "追加内容",
                "icon": "content",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "campaign:write",
                "desc": "DRAFT"
              },
              {
                "id": "end-campaign",
                "title": "结束活动",
                "icon": "check",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "campaign:close",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV: campaign lineage"
      ]
    }
  },
  "BMP-08": {
    "titleKey": "screen.BMP-08",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "播客工作室",
        "titleKey": "screen.BMP-08",
        "desc": "把研究/证据材料转成播客提纲、脚本与成片，AI 仅起草、人工定稿。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "upload",
            "title": "导入研究材料",
            "files": [
              {
                "name": "市场情报 W37.pdf",
                "pct": 100,
                "stage": "已解析 · EV-P01"
              },
              {
                "name": "访谈记录.mp3",
                "pct": 42,
                "stage": "转写中…"
              }
            ],
            "dropTitle": "拖入报告/访谈/数据",
            "dropHint": null
          },
          {
            "type": "ai",
            "thread": [
              {
                "who": "user",
                "text": "基于这些材料生成一期 8 分钟播客提纲。"
              },
              {
                "who": "ai",
                "text": "已生成 3 段结构：市场背景→机会拆解→行动建议，每段标注引用证据。",
                "cites": [
                  "EV-P01",
                  "EV-P02"
                ],
                "tools": [
                  "podcast-skill"
                ]
              }
            ]
          }
        ],
        "side": [
          {
            "type": "steps",
            "items": [
              {
                "label": "材料解析",
                "state": "is-done"
              },
              {
                "label": "提纲",
                "state": "is-done"
              },
              {
                "label": "脚本",
                "state": "is-active"
              },
              {
                "label": "配音",
                "state": null
              },
              {
                "label": "成片",
                "state": null
              }
            ],
            "title": "脚本流水线"
          },
          {
            "type": "actions",
            "title": "制作动作",
            "items": [
              {
                "id": "gen-script",
                "title": "生成完整脚本",
                "icon": "edit",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "podcast:draft",
                "desc": "DRAFT"
              },
              {
                "id": "render",
                "title": "渲染成片",
                "icon": "podcast",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "podcast:render",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-P01",
        "EV-P02"
      ]
    }
  },
  "BMP-09": {
    "titleKey": "screen.BMP-09",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "品牌报告与评估",
        "titleKey": "screen.BMP-09",
        "desc": "品牌资产评估、周期报告与评分，结论均可回溯证据。",
        "actions": [
          {
            "label": "生成评估报告",
            "variant": "primary",
            "id": "gen",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "report:write",
            "ico": "evaluation"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "品牌资产五维",
            "kind": "bar",
            "series": [
              {
                "data": [
                  82,
                  76,
                  80,
                  71,
                  85
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "认知",
              "美誉",
              "传播",
              "体验",
              "忠诚"
            ]
          },
          {
            "type": "table",
            "title": "评估记录",
            "columns": [
              {
                "label": "报告",
                "key": "r"
              },
              {
                "label": "周期",
                "key": "p"
              },
              {
                "label": "综合分",
                "key": "s",
                "numeric": true
              },
              {
                "label": "状态",
                "key": "st",
                "numeric": true,
                "type": "t"
              },
              {
                "label": "证据",
                "key": "ev"
              }
            ],
            "rows": [
              {
                "r": "Q3 品牌资产评估",
                "p": "Q3",
                "s": 82.4,
                "st": "已确认",
                "t": "success",
                "ev": "EV-R01"
              },
              {
                "r": "8 月品牌月报",
                "p": "8月",
                "s": 79.6,
                "st": "已确认",
                "t": "success",
                "ev": "EV-R02"
              },
              {
                "r": "竞品对比评估",
                "p": "近30天",
                "s": "草稿",
                "st": "草稿",
                "t": "warning",
                "ev": "UNKNOWN"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "evidence",
            "title": "评估依据",
            "items": [
              {
                "kind": "Metric",
                "id": "EV-R01",
                "chain": [
                  "Canonical",
                  "Evaluation"
                ],
                "quote": "五维评分来自同口径指标加权。",
                "time": "09-08",
                "source": "eval_engine",
                "conf": 92
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-R01",
        "EV-R02"
      ]
    }
  },
  "BMP-10": {
    "titleKey": "screen.BMP-10",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "品牌风险与事件",
        "titleKey": "screen.BMP-10",
        "desc": "品牌侧风险/舆情事件的监测、分级与处置，复用统一风险引擎。"
      },
      {
        "type": "risks",
        "items": [
          {
            "level": "high",
            "title": "竞品对比稿争议",
            "evidence": "EV-BR01",
            "desc": "对比表述可能引发合规风险。",
            "score": 66
          },
          {
            "level": "med",
            "title": "KOL 翻车风险",
            "evidence": "EV-BR02",
            "desc": "某合作创作者历史争议。",
            "score": 48
          },
          {
            "level": "med",
            "title": "负面话题外溢",
            "evidence": "EV-BR03",
            "desc": "从小红书外溢到微博。",
            "score": 45
          }
        ]
      },
      {
        "type": "events",
        "title": "相关事件",
        "items": [
          {
            "time": "09-09",
            "title": "竞品发布对比内容",
            "desc": "",
            "date": "09-09",
            "level": "med",
            "tags": [
              "竞品"
            ],
            "evidence": "EV-BR01"
          },
          {
            "time": "09-08",
            "title": "KOL 历史言论被翻出",
            "desc": "",
            "date": "09-08",
            "level": "med",
            "tags": [
              "创作者"
            ],
            "evidence": "EV-BR02"
          }
        ],
        "more": true
      },
      {
        "type": "actions",
        "title": "处置",
        "items": [
          {
            "id": "hold-creator",
            "title": "暂停合作创作者",
            "icon": "pause",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "creator:hold",
            "desc": "EFFECT",
            "risk": true
          },
          {
            "id": "draft-response",
            "title": "起草回应口径",
            "icon": "edit",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "response:draft",
            "desc": "DRAFT"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-BR01..03"
      ]
    }
  },
  "BMP-11": {
    "titleKey": "screen.BMP-11",
    "sections": [
      {
        "type": "head",
        "eyebrow": "BMP · 品牌市场",
        "title": "对标与竞品分析",
        "titleKey": "screen.BMP-11",
        "desc": "同口径竞品对标：指标、内容、渠道、价格与节奏，输出差异与证据。"
      },
      {
        "type": "table",
        "title": "竞品对标矩阵",
        "columns": [
          {
            "label": "维度",
            "key": "d"
          },
          {
            "label": "主品牌",
            "key": "a"
          },
          {
            "label": "竞品 X",
            "key": "x"
          },
          {
            "label": "竞品 Y",
            "key": "y"
          },
          {
            "label": "差距",
            "key": "gap",
            "numeric": true,
            "type": "t"
          }
        ],
        "rows": [
          {
            "d": "健康分",
            "a": 82.4,
            "x": 79.8,
            "y": 70.2,
            "gap": "领先",
            "t": "success"
          },
          {
            "d": "声量",
            "a": "28.6k",
            "x": "31.2k",
            "y": "9.0k",
            "gap": "落后 X",
            "t": "warning"
          },
          {
            "d": "互动率",
            "a": "4.8%",
            "x": "5.2%",
            "y": "3.1%",
            "gap": "略落后 X",
            "t": "warning"
          },
          {
            "d": "渠道覆盖",
            "a": "5",
            "x": "5",
            "y": "3",
            "gap": "持平",
            "t": "neutral"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "声量对标趋势",
            "kind": "line",
            "series": [
              {
                "data": [
                  40,
                  44,
                  46,
                  50,
                  52
                ],
                "color": "var(--lum-c-brand-500)"
              },
              {
                "data": [
                  42,
                  46,
                  50,
                  54,
                  58
                ],
                "color": "var(--lum-c-danger)"
              }
            ],
            "labels": [
              "W1",
              "W2",
              "W3",
              "W4",
              "W5"
            ]
          }
        ],
        "side": [
          {
            "type": "insight",
            "text": "竞品 X 以高频短视频拉动声量，我方在互动质量与忠诚维度仍领先，建议补齐短视频频次而非降价。",
            "evidence": [
              "EV-B1101"
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-B1101"
      ]
    }
  },
  "AI-01": {
    "titleKey": "screen.AI-01",
    "sections": [
      {
        "type": "head",
        "eyebrow": "AI Agent",
        "title": "AI 意图入口",
        "titleKey": "screen.AI-01",
        "desc": "从一句任务出发，识别意图、检索证据、生成可追溯结论；AI 是增强层，不拥有生产事实。",
        "actions": [
          {
            "label": "查看 AI Gateway",
            "variant": "secondary",
            "id": "go-AI-05",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "ops"
          },
          {
            "label": "技能中心",
            "variant": "ghost",
            "id": "go-AI-04",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "skill"
          }
        ]
      },
      {
        "type": "raw",
        "html": "\n<div class=\"lum-opt lum-opt-composer\" data-opt=\"composer\" data-strength=\"idle\" data-reveal>\n  <canvas class=\"lum-opt__gl\"></canvas><div class=\"lum-opt__fallback\"></div>\n  <div style=\"padding:20px\">\n    <div class=\"lum-row\" style=\"gap:8px;margin-bottom:10px\">\n      <span class=\"lum-chip lum-press\"><span data-i18n='ai.task_morph'>能力→任务</span></span>\n    </div>\n    <textarea class=\"lum-textarea\" style=\"min-height:84px;background:transparent;border:0;font-size:16px;padding:0\" data-i18n-ph=\"ai.composer_placeholder\" placeholder=\"\"></textarea>\n    <div class=\"lum-row-between\" style=\"margin-top:10px\">\n      <div class=\"lum-row\" style=\"gap:8px\">\n        <button class=\"lum-chip lum-press\">引用证据</button>\n        <button class=\"lum-chip lum-press\">指定主体</button>\n        <button class=\"lum-chip lum-press\">时间范围</button>\n      </div>\n      <button class=\"lum-btn lum-btn-primary\"><span data-i18n='ai.send'>发送</span> →</button>\n    </div>\n  </div>\n</div>"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "今日已锚定证据",
            "value": 1284,
            "icon": "link",
            "source": "EV: evidence_chain",
            "fresh": "live",
            "decimals": 0,
            "delta": 12,
            "deltaUnit": "%",
            "spark": [
              8,
              10,
              9,
              13,
              12,
              15,
              14,
              18,
              16,
              20,
              19,
              22
            ]
          },
          {
            "label": "AI 结论可追溯率",
            "value": 99.2,
            "icon": "evaluation",
            "source": "EV: ai_trace",
            "fresh": "live",
            "decimals": 1,
            "unit": "%",
            "spark": [
              20,
              17,
              22,
              19,
              25,
              21,
              28
            ]
          },
          {
            "label": "Provider 健康",
            "value": 4,
            "icon": "ops",
            "source": "RUNTIME: ai_gateway",
            "fresh": "m5",
            "decimals": 0,
            "unit": "/4"
          },
          {
            "label": "待人工复核",
            "value": 7,
            "icon": "risk",
            "source": "EV: review_queue",
            "fresh": "live",
            "decimals": 0,
            "delta": -3,
            "deltaUnit": ""
          }
        ]
      },
      {
        "type": "cards",
        "items": [
          {
            "title": "生成商业运营简报",
            "desc": "汇总主体下指标/事件/风险并标注证据链",
            "ico": "report",
            "badge": {
              "text": "商业运营",
              "cls": "brand"
            }
          },
          {
            "title": "追踪一个新事件",
            "desc": "沿 Source→Event→Case 建立时间线与影响面",
            "ico": "event"
          },
          {
            "title": "对比竞品传播表现",
            "desc": "多品牌同口径对比，输出差异与证据",
            "ico": "target"
          },
          {
            "title": "起草内容并走审批",
            "desc": "生成草稿进入 DRAFT，经权限后才执行",
            "ico": "content"
          }
        ],
        "cols": 4
      },
      {
        "type": "split",
        "main": [
          {
            "type": "timeline",
            "title": "最近任务",
            "items": [
              {
                "time": "09:41",
                "title": "北区客流环比分析",
                "desc": "已完成 · 引用 6 条证据",
                "done": true
              },
              {
                "time": "09:12",
                "title": "负面评论聚类",
                "desc": "已完成 · 3 个簇",
                "done": true
              },
              {
                "time": "08:50",
                "title": "周报初稿",
                "desc": "等待人工确认",
                "done": false
              },
              {
                "time": "昨日",
                "title": "会员日 Campaign 复盘",
                "desc": "已归档",
                "done": true
              }
            ],
            "label": "History"
          }
        ],
        "side": [
          {
            "type": "runtime",
            "title": "Provider 状态",
            "items": [
              {
                "name": "智谱 glm-5.3",
                "state": "ok",
                "detail": "200 · 1.2s"
              },
              {
                "name": "本地 Ollama",
                "state": "ok",
                "detail": "local"
              },
              {
                "name": "规则引擎",
                "state": "ok",
                "detail": "deterministic"
              },
              {
                "name": "备用通道",
                "state": "idle",
                "detail": "standby"
              }
            ]
          },
          {
            "type": "note",
            "text": "AI 输出为派生结果，携带 Provider/Model/Prompt/Confidence/Evidence 引用与人工修正状态，不覆盖原始 Evidence 或 Canonical Data。",
            "kind": "RULE",
            "code": "AI-NOT-TRUTH"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV: evidence_chain（全局）",
        "EV: subject_context v2.1",
        "RUNTIME: ai_gateway"
      ]
    }
  },
  "AI-02": {
    "titleKey": "screen.AI-02",
    "sections": [
      {
        "type": "head",
        "eyebrow": "AI Agent",
        "title": "能力 → 任务工作台",
        "titleKey": "screen.AI-02",
        "desc": "选择能力后，表面发生 Morph：旧能力后退、任务上下文进入、证据落定；全过程可中断。"
      },
      {
        "type": "steps",
        "items": [
          {
            "label": "识别意图",
            "state": "is-done"
          },
          {
            "label": "能力后退",
            "state": "is-done"
          },
          {
            "label": "表面 Morph",
            "state": "is-active"
          },
          {
            "label": "上下文解析",
            "state": null
          },
          {
            "label": "内容进入",
            "state": null
          },
          {
            "label": "证据落定",
            "state": null
          }
        ]
      },
      {
        "type": "raw",
        "html": "<div class=\"lum-opt lum-opt-morph\" data-opt=\"morph\" data-strength=\"composing\" data-reveal>\n    <canvas class=\"lum-opt__gl\"></canvas><div class=\"lum-opt__fallback\"></div>\n    <div style=\"padding:18px;position:relative\" class=\"lum-row-between\">\n      <div><div class=\"lum-eyebrow\">CAPABILITY</div><b style=\"font-size:18px\">传播分析 Communication Analysis</b></div>\n      <svg width='26' height='26' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8'><path d='M5 12h14M13 6l6 6-6 6'/></svg><div><div class=\"lum-eyebrow\">TASK</div><b style=\"font-size:18px\">对比近 30 天小红书 vs 微博声量</b></div>\n    </div></div>"
      },
      {
        "type": "ai",
        "steps": [
          {
            "label": "识别意图：跨平台声量对比",
            "state": "done",
            "tool": "intent"
          },
          {
            "label": "检索 Subject 范围内已确认证据",
            "state": "done",
            "tool": "evidence_store"
          },
          {
            "label": "按统一口径计算趋势",
            "state": "done",
            "tool": "canonical_metrics"
          },
          {
            "label": "生成结论并标注引用",
            "state": "running",
            "tool": "llm:glm-5.3"
          }
        ],
        "children": "<div style=\"margin-top:6px\"></div>"
      },
      {
        "type": "evidence",
        "title": "本任务引用的证据",
        "items": [
          {
            "kind": "Canonical",
            "id": "EV-7731",
            "chain": [
              "Source 小红书",
              "Canonical",
              "Metric"
            ],
            "quote": "近 30 天小红书提及 4,218 条，环比 +18.4%。",
            "time": "09:42",
            "source": "xhs.collector",
            "conf": 96
          },
          {
            "kind": "Canonical",
            "id": "EV-7732",
            "chain": [
              "Source 微博",
              "Canonical",
              "Metric"
            ],
            "quote": "同期微博提及 2,106 条，环比 +3.1%。",
            "time": "09:42",
            "source": "weibo.collector",
            "conf": 95
          }
        ]
      },
      {
        "type": "actions",
        "title": "下一步",
        "items": [
          {
            "id": "insert-to-report",
            "title": "插入到周报草稿",
            "icon": "report",
            "cls": "NAVIGATION",
            "scope": "report:draft",
            "target": "weekly_report",
            "permission": "report:write",
            "desc": "DRAFT"
          },
          {
            "id": "save-task",
            "title": "保存为可复用任务",
            "icon": "folder",
            "cls": "NAVIGATION",
            "scope": "user:self",
            "target": "task_library",
            "permission": "task:write",
            "desc": "QUERY"
          },
          {
            "id": "run-effect",
            "title": "推送到协作群",
            "icon": "message",
            "cls": "NAVIGATION",
            "scope": "channel:external",
            "target": "im_webhook",
            "permission": "notify:write",
            "desc": "EFFECT",
            "risk": true
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7731",
        "EV-7732",
        "EV: ai_trace"
      ]
    }
  },
  "AI-03": {
    "titleKey": "screen.AI-03",
    "sections": [
      {
        "type": "head",
        "eyebrow": "AI Agent",
        "title": "证据锚定分析线程",
        "titleKey": "screen.AI-03",
        "desc": "每条 AI 结论都可回跳到 Evidence；缺证据的推断显式标 UNKNOWN，不编造。"
      },
      {
        "type": "ai",
        "thread": [
          {
            "who": "user",
            "text": "帮我判断本周负面是否在升温，并给出处置优先级。"
          },
          {
            "who": "ai",
            "text": "本周负面声量环比 +9.6%，主要集中在「停车体验」与「北区指引」两个簇；建议优先处理停车体验（风险分 72）。",
            "cites": [
              "EV-7701",
              "EV-7704",
              "EV-7710"
            ],
            "tools": [
              "canonical_metrics",
              "risk_engine"
            ]
          },
          {
            "who": "user",
            "text": "和上周同期相比，哪个时段最集中？"
          },
          {
            "who": "ai",
            "text": "工作日 18:00–21:00 占负面增量的 47%，与离场高峰重合；该结论由 312 条已确认评论聚合。",
            "cites": [
              "EV-7711"
            ]
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "evidence",
            "title": "结论引用",
            "items": [
              {
                "kind": "Metric",
                "id": "EV-7701",
                "chain": [
                  "Comment",
                  "Canonical",
                  "Metric"
                ],
                "quote": "本周负面 312 条，上周 285 条。",
                "time": "09:30",
                "source": "comment.canonical",
                "conf": 99
              },
              {
                "kind": "Cluster",
                "id": "EV-7704",
                "chain": [
                  "Comment",
                  "Cluster",
                  "Finding"
                ],
                "quote": "「停车体验」簇 96 条，占比 30.8%。",
                "time": "09:31",
                "source": "cluster.rule",
                "conf": 93
              },
              {
                "kind": "Risk",
                "id": "EV-7710",
                "chain": [
                  "Finding",
                  "Risk"
                ],
                "quote": "停车体验风险分 72（高），趋势上行。",
                "time": "09:32",
                "source": "risk_engine",
                "conf": 90
              }
            ]
          }
        ],
        "side": [
          {
            "type": "risks",
            "items": [
              {
                "level": "high",
                "title": "停车体验负面升温",
                "evidence": "EV-7710",
                "desc": "18–21 点离场高峰集中，建议增派引导。",
                "score": 72
              },
              {
                "level": "med",
                "title": "北区指引不清",
                "evidence": "EV-7712",
                "desc": "指示牌缺失导致绕路投诉，占 18%。",
                "score": 48
              }
            ]
          },
          {
            "type": "actions",
            "title": "建议行动",
            "items": [
              {
                "id": "create-case",
                "title": "生成处置 Case",
                "icon": "case",
                "cls": "NAVIGATION",
                "scope": "subject:current",
                "target": "case",
                "permission": "case:write",
                "desc": "DRAFT"
              },
              {
                "id": "assign-owner",
                "title": "指派责任人",
                "icon": "user",
                "cls": "NAVIGATION",
                "scope": "team:ops",
                "target": "assignment",
                "permission": "team:assign",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7701",
        "EV-7704",
        "EV-7710",
        "EV-7711"
      ]
    }
  },
  "AI-04": {
    "titleKey": "screen.AI-04",
    "sections": [
      {
        "type": "head",
        "eyebrow": "AI Agent",
        "title": "Agent / 技能中心",
        "titleKey": "screen.AI-04",
        "desc": "所有 Agent/Skill 必须有真实调用链与权限边界；文件存在不等于能力可用。",
        "actions": [
          {
            "label": "仅看可用",
            "variant": "secondary",
            "id": "",
            "cls": "NAVIGATION",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "evaluation"
          }
        ]
      },
      {
        "type": "filters",
        "chips": [
          {
            "label": "全部",
            "on": true
          },
          {
            "label": "商业运营",
            "on": false
          },
          {
            "label": "品牌市场",
            "on": false
          },
          {
            "label": "采集",
            "on": false
          },
          {
            "label": "分析",
            "on": false
          },
          {
            "label": "创作",
            "on": false
          },
          {
            "label": "系统",
            "on": false
          }
        ]
      },
      {
        "type": "cards",
        "items": [
          {
            "title": "证据检索 Agent",
            "desc": "沿证据链检索并回标来源，状态 VERIFIED",
            "ico": "link",
            "badge": {
              "text": "VERIFIED",
              "cls": "success"
            }
          },
          {
            "title": "事件聚类 Skill",
            "desc": "规则+模型聚类评论/帖子",
            "ico": "event",
            "badge": {
              "text": "VERIFIED",
              "cls": "success"
            }
          },
          {
            "title": "内容草稿 Agent",
            "desc": "生成多平台草稿，进入 DRAFT 审批",
            "ico": "content",
            "badge": {
              "text": "PARTIAL",
              "cls": "warning"
            }
          },
          {
            "title": "播客脚本 Skill",
            "desc": "把研究材料转成播客提纲",
            "ico": "podcast",
            "badge": {
              "text": "PARTIAL",
              "cls": "warning"
            }
          },
          {
            "title": "自动处置 Agent",
            "desc": "EFFECT 类，默认禁用，需审批",
            "ico": "shield-off",
            "badge": {
              "text": "BLOCKED",
              "cls": "danger"
            }
          },
          {
            "title": "跨仓研究桥",
            "desc": "仅研发侧参考，非运行时依赖",
            "ico": "research",
            "badge": {
              "text": "LEGACY",
              "cls": "neutral"
            }
          }
        ],
        "cols": 3
      },
      {
        "type": "table",
        "title": "Agent / Skill 调用链",
        "columns": [
          {
            "label": "名称",
            "key": "name"
          },
          {
            "label": "领域",
            "key": "domain"
          },
          {
            "label": "类型",
            "key": "kind"
          },
          {
            "label": "权限",
            "key": "perm"
          },
          {
            "label": "调用链状态",
            "key": "state",
            "numeric": true,
            "type": "stateTone"
          },
          {
            "label": "证据",
            "key": "ev"
          }
        ],
        "rows": [
          {
            "name": "证据检索 Agent",
            "domain": "共享能力",
            "kind": "检索",
            "perm": "evidence:read",
            "state": "VERIFIED",
            "stateTone": "success",
            "ev": "EV-AG-01"
          },
          {
            "name": "事件聚类 Skill",
            "domain": "商业运营",
            "kind": "规则+模型",
            "perm": "content:read",
            "state": "VERIFIED",
            "stateTone": "success",
            "ev": "EV-AG-02"
          },
          {
            "name": "内容草稿 Agent",
            "domain": "共享能力",
            "kind": "生成",
            "perm": "content:draft",
            "state": "PARTIAL",
            "stateTone": "warning",
            "ev": "UNKNOWN"
          },
          {
            "name": "自动处置 Agent",
            "domain": "系统层",
            "kind": "执行",
            "perm": "effect:write",
            "state": "BLOCKED",
            "stateTone": "danger",
            "ev": "—"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV: skill_registry",
        "EV: agent call graph"
      ]
    }
  },
  "AI-05": {
    "titleKey": "screen.AI-05",
    "sections": [
      {
        "type": "head",
        "eyebrow": "AI Agent",
        "title": "AI Gateway 与 Provider",
        "titleKey": "screen.AI-05",
        "desc": "Provider 不可用时核心生产链由规则与数据继续运行；云 AI 不是启动硬依赖。"
      },
      {
        "type": "runtime",
        "title": "Provider 实时状态",
        "items": [
          {
            "name": "智谱 glm-5.3（深度推理）",
            "state": "ok",
            "detail": "healthy · 1.2s · balance ok"
          },
          {
            "name": "智谱 glm-4.5-air（快速）",
            "state": "ok",
            "detail": "healthy · 0.4s"
          },
          {
            "name": "本地 Ollama",
            "state": "ok",
            "detail": "local fallback"
          },
          {
            "name": "确定性规则引擎",
            "state": "ok",
            "detail": "always-on"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "近 24h 调用量（按 Provider）",
            "kind": "line",
            "series": [
              {
                "data": [
                  12,
                  18,
                  15,
                  22,
                  30,
                  26,
                  34,
                  40,
                  38,
                  46,
                  52,
                  48
                ],
                "color": "var(--lum-c-brand-500)"
              },
              {
                "data": [
                  4,
                  6,
                  5,
                  8,
                  7,
                  9,
                  11,
                  10,
                  12,
                  13,
                  12,
                  14
                ],
                "color": "var(--lum-c-success)"
              }
            ],
            "labels": [
              "00",
              "02",
              "04",
              "06",
              "08",
              "10",
              "12",
              "14",
              "16",
              "18",
              "20",
              "22"
            ],
            "legend": [
              {
                "label": "智谱",
                "color": "var(--lum-c-brand-500)"
              },
              {
                "label": "本地",
                "color": "var(--lum-c-success)"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "kpis",
            "items": [
              {
                "label": "今日调用",
                "value": 1842,
                "icon": "ops",
                "source": "RUNTIME:ai_gateway",
                "fresh": "live",
                "decimals": 0,
                "delta": 8,
                "deltaUnit": "%"
              },
              {
                "label": "规则兜底率",
                "value": 6.4,
                "icon": "skill",
                "source": "RUNTIME:rules",
                "fresh": "live",
                "decimals": 1,
                "unit": "%"
              }
            ]
          },
          {
            "type": "note",
            "text": "降级策略：云端失败→本地模型→确定性规则；任何一层失败都不阻塞 Evidence/Canonical 主链。",
            "kind": "RULE",
            "code": "AI-FALLBACK"
          }
        ]
      },
      {
        "type": "table",
        "title": "Provider 配置",
        "columns": [
          {
            "label": "Provider",
            "key": "n"
          },
          {
            "label": "用途",
            "key": "use"
          },
          {
            "label": "状态",
            "key": "s",
            "numeric": true,
            "type": "t"
          },
          {
            "label": "延迟ms",
            "key": "lat",
            "numeric": true
          }
        ],
        "rows": [
          {
            "n": "glm-5.3",
            "use": "深度推理",
            "s": "OK",
            "t": "success",
            "lat": 1204
          },
          {
            "n": "glm-4.5-air",
            "use": "日常快速",
            "s": "OK",
            "t": "success",
            "lat": 410
          },
          {
            "n": "ollama-local",
            "use": "本地兜底",
            "s": "OK",
            "t": "success",
            "lat": 88
          },
          {
            "n": "legacy-provider",
            "use": "历史通道",
            "s": "STANDBY",
            "t": "neutral",
            "lat": "—"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "RUNTIME: ai_gateway",
        "EV: provider health"
      ]
    }
  },
  "SYS-01": {
    "titleKey": "screen.SYS-01",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "运行时健康 Runtime Health",
        "titleKey": "screen.SYS-01",
        "desc": "唯一生产 Runtime 的进程、端口、依赖与降级状态；启动链与健康检查可追溯。",
        "actions": [
          {
            "label": "运行时身份",
            "variant": "secondary",
            "id": "identity",
            "cls": "QUERY",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "runtime"
          },
          {
            "label": "重启服务",
            "variant": "ghost",
            "id": "restart",
            "cls": "EFFECT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "runtime:restart",
            "ico": "refresh",
            "risk": true
          }
        ]
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "在线进程",
            "value": 7,
            "icon": "runtime",
            "source": "RUNTIME: process",
            "fresh": "live",
            "decimals": 0,
            "unit": "/7"
          },
          {
            "label": "健康检查",
            "value": 24,
            "icon": "check",
            "source": "RUNTIME: health",
            "fresh": "live",
            "decimals": 0,
            "unit": "/24"
          },
          {
            "label": "平均响应",
            "value": 142,
            "icon": "trend",
            "source": "RUNTIME: latency",
            "fresh": "live",
            "decimals": 0,
            "unit": "ms"
          },
          {
            "label": "降级中",
            "value": 0,
            "icon": "alert",
            "source": "RUNTIME: degraded",
            "fresh": "live",
            "decimals": 0
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "runtime",
            "title": "核心服务",
            "items": [
              {
                "name": "Web/API (0.0.0.0:8201)",
                "state": "ok",
                "detail": "listening"
              },
              {
                "name": "Canonical 主链",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "Evidence 服务",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "Metric 引擎",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "Scheduler",
                "state": "ok",
                "detail": "running"
              },
              {
                "name": "AI Gateway",
                "state": "ok",
                "detail": "running (非硬依赖)"
              },
              {
                "name": "内部浏览器",
                "state": "idle",
                "detail": "standby"
              }
            ]
          },
          {
            "type": "chart",
            "title": "近 1h 请求与延迟",
            "kind": "line",
            "series": [
              {
                "data": [
                  120,
                  140,
                  132,
                  150,
                  142,
                  138,
                  142
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "-60",
              "-50",
              "-40",
              "-30",
              "-20",
              "-10",
              "now"
            ]
          }
        ],
        "side": [
          {
            "type": "note",
            "text": "Runtime 启动链：scripts/start_production.ps1 → run_supervised.py → app factory → blueprint 注册；Canonical 启动身份以 /api/runtime/identity 为准。",
            "kind": "RULE",
            "code": "RUNTIME-ENTRY"
          },
          {
            "type": "actions",
            "title": "运行时操作",
            "items": [
              {
                "id": "view-identity",
                "title": "查看运行时身份",
                "icon": "runtime",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "QUERY"
              },
              {
                "id": "graceful-reload",
                "title": "平滑重载",
                "icon": "refresh",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "runtime:reload",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "RUNTIME: process/health/identity"
      ]
    }
  },
  "SYS-02": {
    "titleKey": "screen.SYS-02",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "采集器状态 Collector",
        "titleKey": "screen.SYS-02",
        "desc": "各平台采集任务的调度、限流、退避与入链情况；采集失败不污染 Canonical。"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "活跃采集器",
            "value": 5,
            "icon": "collector",
            "source": "RUNTIME:collector",
            "fresh": "live",
            "decimals": 0,
            "unit": "/6"
          },
          {
            "label": "今日采集",
            "value": 38420,
            "icon": "download",
            "source": "EV:ingest",
            "fresh": "live",
            "decimals": 0,
            "delta": 9,
            "deltaUnit": "%"
          },
          {
            "label": "限流退避",
            "value": 1,
            "icon": "alert",
            "source": "RUNTIME:collector",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "入链失败",
            "value": 0,
            "icon": "check",
            "source": "EV:ingest",
            "fresh": "live",
            "decimals": 0
          }
        ]
      },
      {
        "type": "table",
        "title": "采集任务",
        "columns": [
          {
            "label": "采集器",
            "key": "n"
          },
          {
            "label": "平台",
            "key": "p"
          },
          {
            "label": "状态",
            "key": "s",
            "numeric": true,
            "type": "t"
          },
          {
            "label": "频率",
            "key": "f"
          },
          {
            "label": "最近成功",
            "key": "ok"
          },
          {
            "label": "待处理",
            "key": "q",
            "numeric": true
          },
          {
            "label": "证据",
            "key": "ev"
          }
        ],
        "rows": [
          {
            "n": "小红书采集",
            "p": "小红书",
            "s": "运行",
            "t": "success",
            "f": "2m",
            "ok": "10:22",
            "q": 12,
            "ev": "COL-01"
          },
          {
            "n": "微博采集",
            "p": "微博",
            "s": "运行",
            "t": "success",
            "f": "3m",
            "ok": "10:21",
            "q": 4,
            "ev": "COL-02"
          },
          {
            "n": "点评采集",
            "p": "大众点评",
            "s": "退避",
            "t": "warning",
            "f": "限流",
            "ok": "10:05",
            "q": 0,
            "ev": "COL-03"
          },
          {
            "n": "评论同步",
            "p": "会员/评论",
            "s": "运行",
            "t": "success",
            "f": "5m",
            "ok": "10:20",
            "q": 2,
            "ev": "COL-04"
          },
          {
            "n": "闸机/会员",
            "p": "内部系统",
            "s": "运行",
            "t": "success",
            "f": "1m",
            "ok": "10:22",
            "q": 0,
            "ev": "COL-05"
          },
          {
            "n": "外部 API",
            "p": "第三方",
            "s": "待机",
            "t": "neutral",
            "f": "手动",
            "ok": "昨日",
            "q": 0,
            "ev": "COL-06"
          }
        ]
      },
      {
        "type": "note",
        "text": "原始数据先入隔离区，经去重/校验/证据固定后才进入 Canonical；采集层异常只标记，不用 0 静默填充。",
        "kind": "RULE",
        "code": "INGEST-GUARD"
      }
    ],
    "context": {
      "evidence": [
        "COL-01..06"
      ]
    }
  },
  "SYS-03": {
    "titleKey": "screen.SYS-03",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "数据库与事实链 Database & Truth Chain",
        "titleKey": "screen.SYS-03",
        "desc": "schema_version 不等于应用可读；展示版本、完整性、外键、Canonical 链路与隔离契约。"
      },
      {
        "type": "kpis",
        "items": [
          {
            "label": "Schema 版本",
            "value": "v12",
            "icon": "database",
            "source": "DB: schema_version",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "完整性检查",
            "value": "ok",
            "icon": "check",
            "source": "DB: integrity_check",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "外键违规",
            "value": 0,
            "icon": "link",
            "source": "DB: foreign_key_check",
            "fresh": "live",
            "decimals": 0
          },
          {
            "label": "Canonical 表",
            "value": 64,
            "icon": "layers",
            "source": "DB: canonical",
            "fresh": "live",
            "decimals": 0
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "timeline",
            "title": "事实链",
            "items": [
              {
                "time": "Source",
                "title": "原始来源固定（快照/链接/时间）",
                "desc": null,
                "done": true
              },
              {
                "time": "Evidence",
                "title": "证据固定 + 置信度",
                "desc": null,
                "done": true
              },
              {
                "time": "Canonical",
                "title": "去重归一为 Canonical",
                "desc": null,
                "done": true
              },
              {
                "time": "Metric",
                "title": "同口径指标",
                "desc": null,
                "done": true
              },
              {
                "time": "View Model",
                "title": "面向界面的归一模型",
                "desc": null,
                "done": true
              }
            ],
            "label": null
          },
          {
            "type": "table",
            "title": "数据库身份",
            "columns": [
              {
                "label": "项",
                "key": "k"
              },
              {
                "label": "值",
                "key": "v"
              }
            ],
            "rows": [
              {
                "k": "当前连接身份",
                "v": "ZBC_DB_PATH（隔离）"
              },
              {
                "k": "受保护生产库",
                "v": "只读 / 禁写"
              },
              {
                "k": "WAL/SHM",
                "v": "测试不触碰"
              },
              {
                "k": "外键运行时",
                "v": "写连接 ON（分批）"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "note",
            "text": "version=v12 仅代表迁移跑完；必须再过 Required Schema/Table Contract、Application Readability、Runtime 三道 Gate。",
            "kind": "RULE",
            "code": "V12-NOT-READY"
          },
          {
            "type": "risks",
            "items": [
              {
                "level": "med",
                "title": "历史 ai_task 孤儿 4 行",
                "evidence": "P0C-B",
                "desc": "历史数据债，未做依赖追踪前不删。"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "DB: integrity/foreign_key",
        "P0C evidence"
      ]
    }
  },
  "SYS-04": {
    "titleKey": "screen.SYS-04",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "安全与权限 Security & Permission",
        "titleKey": "screen.SYS-04",
        "desc": "READ/TASK/AUDIT/WRITE/DEPLOY 五级边界；EFFECT 行动必须二次确认与权限校验。"
      },
      {
        "type": "table",
        "title": "权限矩阵",
        "columns": [
          {
            "label": "能力域",
            "key": "d"
          },
          {
            "label": "READ",
            "key": "r"
          },
          {
            "label": "TASK",
            "key": "t"
          },
          {
            "label": "AUDIT",
            "key": "a"
          },
          {
            "label": "WRITE",
            "key": "w"
          },
          {
            "label": "DEPLOY",
            "key": "dp"
          }
        ],
        "rows": [
          {
            "d": "Evidence/Canonical",
            "r": "✓",
            "t": "✓",
            "a": "✓",
            "w": "受限",
            "dp": "—"
          },
          {
            "d": "报告导出",
            "r": "✓",
            "t": "✓",
            "a": "✓",
            "w": "草稿",
            "dp": "—"
          },
          {
            "d": "内容发布",
            "r": "✓",
            "t": "草稿",
            "a": "✓",
            "w": "审批",
            "dp": "—"
          },
          {
            "d": "生产部署",
            "r": "管理员",
            "t": "—",
            "a": "✓",
            "w": "管理员",
            "dp": "管理员"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "risks",
            "items": [
              {
                "level": "high",
                "title": "越权写入风险",
                "evidence": "SEC-01",
                "desc": "任何 EFFECT 必须后端重验 Subject/Scope 授权。"
              },
              {
                "level": "med",
                "title": "凭据泄漏面",
                "evidence": "SEC-02",
                "desc": ".env/key 不进前端与交付物。"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "actions",
            "title": "审计操作",
            "items": [
              {
                "id": "view-audit",
                "title": "查看审计日志",
                "icon": "ops",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "audit:read",
                "desc": "QUERY"
              },
              {
                "id": "rotate-key",
                "title": "轮换密钥",
                "icon": "security",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "secret:rotate",
                "desc": "EFFECT",
                "risk": true
              }
            ]
          },
          {
            "type": "note",
            "text": "前端只做交互确认；真正授权判定在后端，Subject 切换不改变数据归属，后端必须重验。",
            "kind": "RULE",
            "code": "PERM-BACKEND"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "SEC-01",
        "SEC-02"
      ]
    }
  },
  "SYS-05": {
    "titleKey": "screen.SYS-05",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "设置 / 外观 / 语言",
        "titleKey": "screen.SYS-05",
        "desc": "主题、光学档位、语言（zh/en/ko）、密度与动效偏好；偏好不外溢为业务数据。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "form",
            "title": "外观",
            "fields": [
              {
                "label": "主题",
                "type": "select",
                "ph": "",
                "opts": [
                  "浅色 Light",
                  "深色 Dark",
                  "跟随系统"
                ]
              },
              {
                "label": "光学效果",
                "type": "select",
                "ph": "",
                "opts": [
                  "高（WebGL）",
                  "标准",
                  "软玻璃",
                  "不透明（降级）"
                ]
              },
              {
                "label": "界面密度",
                "type": "select",
                "ph": "",
                "opts": [
                  "舒适",
                  "紧凑"
                ]
              },
              {
                "label": "减弱动效",
                "type": "select",
                "ph": "",
                "opts": [
                  "跟随系统",
                  "开启",
                  "关闭"
                ]
              }
            ],
            "actions": [
              {
                "label": "保存偏好",
                "variant": "primary",
                "id": "save-pref",
                "cls": "DRAFT",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "pref:write",
                "ico": "check"
              },
              {
                "label": "重置",
                "variant": "ghost",
                "id": "",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "form",
            "title": "语言与区域",
            "fields": [
              {
                "label": "界面语言",
                "type": "select",
                "ph": "",
                "opts": [
                  "简体中文",
                  "English",
                  "한국어"
                ]
              },
              {
                "label": "时区",
                "type": "select",
                "ph": "",
                "opts": [
                  "本地",
                  "UTC"
                ]
              },
              {
                "label": "数字/货币格式",
                "type": "select",
                "ph": "",
                "opts": [
                  "跟随语言",
                  "自定义"
                ]
              }
            ]
          },
          {
            "type": "note",
            "text": "固定 UI 文案走 i18n key（三语 parity）；业务数据走 ViewModel，不进 locale。另提供 pseudo-expanded 130%/150% 文本压力测试。",
            "kind": "RULE",
            "code": "I18N-SPLIT"
          }
        ]
      }
    ],
    "context": {
      "evidence": []
    }
  },
  "SYS-06": {
    "titleKey": "screen.SYS-06",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "内部浏览器",
        "titleKey": "screen.SYS-06",
        "desc": "受控采集/取证浏览器：页面快照、证据固定与操作审计，不与个人浏览混用。",
        "actions": [
          {
            "label": "新标签",
            "variant": "primary",
            "id": "new-tab",
            "cls": "TASK",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "browser:open",
            "ico": "browser"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "raw",
            "html": "<section class=\"lum-card\" style=\"padding:0;overflow:hidden\" data-reveal>\n      <div class=\"lum-row\" style=\"gap:8px;padding:10px 12px;border-bottom:1px solid var(--lum-line)\">\n        <span class=\"lum-chip\">←</span><span class=\"lum-chip\">→</span><span class=\"lum-chip\">⟳</span>\n        <div class=\"lum-search\" style=\"flex:1\">https://www.example.com/subject</div><span class=\"lum-badge lum-badge-success\">已固定证据</span></div>\n      <div style=\"height:280px;display:grid;place-items:center;background:var(--lum-surface-2);color:var(--lum-text-3)\">受控浏览视口（原型占位 · 不加载真实外站）</div></section>"
          }
        ],
        "side": [
          {
            "type": "runtime",
            "title": "浏览器状态",
            "items": [
              {
                "name": "隔离上下文",
                "state": "ok",
                "detail": "separate profile"
              },
              {
                "name": "证据固定",
                "state": "ok",
                "detail": "snapshot+hash"
              },
              {
                "name": "操作审计",
                "state": "ok",
                "detail": "recorded"
              }
            ]
          },
          {
            "type": "actions",
            "title": "取证",
            "items": [
              {
                "id": "snapshot",
                "title": "固定快照为证据",
                "icon": "link",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "evidence:capture",
                "desc": "DRAFT"
              },
              {
                "id": "extract",
                "title": "抽取结构化数据",
                "icon": "layers",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "TASK"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "浏览器快照证据"
      ]
    }
  },
  "SYS-07": {
    "titleKey": "screen.SYS-07",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "验收评估 Evaluation / Acceptance",
        "titleKey": "screen.SYS-07",
        "desc": "Production Acceptance 六 Gate 状态；PARTIAL/UNKNOWN 不算 PASS，文档存在不算通过。"
      },
      {
        "type": "steps",
        "items": [
          {
            "label": "G1 P0=0",
            "state": "is-active"
          },
          {
            "label": "G2 仓库完整性",
            "state": null
          },
          {
            "label": "G3 生产事实",
            "state": null
          },
          {
            "label": "G4 Runtime+E2E",
            "state": null
          },
          {
            "label": "G5 安全恢复",
            "state": null
          },
          {
            "label": "G6 发布血缘/回滚",
            "state": null
          }
        ]
      },
      {
        "type": "table",
        "title": "六 Gate",
        "columns": [
          {
            "label": "Gate",
            "key": "g"
          },
          {
            "label": "标准",
            "key": "c"
          },
          {
            "label": "状态",
            "key": "s",
            "numeric": true,
            "type": "t"
          },
          {
            "label": "证据",
            "key": "ev"
          }
        ],
        "rows": [
          {
            "g": "G1 P0",
            "c": "P0 阻塞=0",
            "s": "进行中",
            "t": "warning",
            "ev": "—"
          },
          {
            "g": "G2 仓库",
            "c": "完整性/隔离",
            "s": "未开始",
            "t": "neutral",
            "ev": "—"
          },
          {
            "g": "G3 事实",
            "c": "Truth Owner 唯一",
            "s": "未开始",
            "t": "neutral",
            "ev": "—"
          },
          {
            "g": "G4 Runtime",
            "c": "启动+关键 E2E",
            "s": "未开始",
            "t": "neutral",
            "ev": "—"
          },
          {
            "g": "G5 安全",
            "c": "权限+恢复",
            "s": "未开始",
            "t": "neutral",
            "ev": "—"
          },
          {
            "g": "G6 发布",
            "c": "血缘+回滚演练",
            "s": "未开始",
            "t": "neutral",
            "ev": "—"
          }
        ]
      },
      {
        "type": "note",
        "text": "体验层交付只声明 DOUBAO_EXPERIENCE_HANDOFF=COMPLETE；Production Ready 必须六 Gate 全 PASS，由 Codex 闭环。",
        "kind": "RULE",
        "code": "SIX-GATE"
      }
    ],
    "context": {
      "evidence": [
        "acceptance gates"
      ]
    }
  },
  "SYS-08": {
    "titleKey": "screen.SYS-08",
    "sections": [
      {
        "type": "head",
        "eyebrow": "System",
        "title": "可观测 / 日志 Observability & Logs",
        "titleKey": "screen.SYS-08",
        "desc": "结构化日志、Trace、错误聚合与链路；区分前端原型日志与后端运行时日志。",
        "actions": [
          {
            "label": "导出日志",
            "variant": "secondary",
            "id": "export-log",
            "cls": "QUERY",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "UNKNOWN",
            "ico": "download"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "chart",
            "title": "错误率 / 吞吐",
            "kind": "line",
            "series": [
              {
                "data": [
                  2,
                  1,
                  3,
                  1,
                  0,
                  1,
                  1
                ],
                "color": "var(--lum-c-danger)"
              },
              {
                "data": [
                  40,
                  52,
                  48,
                  60,
                  58,
                  55,
                  62
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "-60",
              "-50",
              "-40",
              "-30",
              "-20",
              "-10",
              "now"
            ]
          },
          {
            "type": "table",
            "title": "最近日志",
            "columns": [
              {
                "label": "时间",
                "key": "t"
              },
              {
                "label": "级别",
                "key": "l",
                "numeric": true,
                "type": "lt"
              },
              {
                "label": "模块",
                "key": "m"
              },
              {
                "label": "消息",
                "key": "msg"
              },
              {
                "label": "Trace",
                "key": "tr"
              }
            ],
            "rows": [
              {
                "t": "10:22:01",
                "l": "INFO",
                "lt": "success",
                "m": "canonical",
                "msg": "ingest batch committed n=128",
                "tr": "tr-9f21"
              },
              {
                "t": "10:21:44",
                "l": "WARN",
                "lt": "warning",
                "m": "collector.dianping",
                "msg": "rate-limit backoff 30s",
                "tr": "tr-9f1e"
              },
              {
                "t": "10:20:10",
                "l": "ERROR",
                "lt": "danger",
                "m": "ai_gateway",
                "msg": "provider timeout -> local fallback",
                "tr": "tr-9f0a"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "runtime",
            "title": "链路",
            "items": [
              {
                "name": "Log 采集",
                "state": "ok",
                "detail": ""
              },
              {
                "name": "Trace 关联",
                "state": "ok",
                "detail": ""
              },
              {
                "name": "错误聚合",
                "state": "ok",
                "detail": ""
              },
              {
                "name": "告警",
                "state": "idle",
                "detail": ""
              }
            ]
          },
          {
            "type": "note",
            "text": "AI 超时已按规则降级到本地/规则引擎，主链未阻塞（见 AI-05 降级策略）。",
            "kind": "RULE",
            "code": "OBS-FALLBACK"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "RUNTIME: logs/trace"
      ]
    }
  },
  "SH-01": {
    "titleKey": "screen.SH-01",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Shared · 序境·内容创作",
        "title": "内容创作工作室 Content Studio",
        "titleKey": "screen.SH-01",
        "desc": "Brief→Context→Evidence→Strategy→Create→Review→Approval→Export→Evaluation→Learning；AI 只按真实 Brief/Evidence 起草原创产物，定稿与发布在人。",
        "actions": [
          {
            "label": "新建 Brief",
            "variant": "primary",
            "id": "new-brief",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "content:draft",
            "ico": "content"
          }
        ]
      },
      {
        "type": "steps",
        "items": [
          {
            "label": "Brief · 真实简报",
            "state": "done"
          },
          {
            "label": "Context · 主体/品牌",
            "state": "done"
          },
          {
            "label": "Evidence · 事实素材",
            "state": "done"
          },
          {
            "label": "Strategy · 叙事策略",
            "state": "done"
          },
          {
            "label": "Create · 原创产物",
            "state": "active"
          },
          {
            "label": "Review · 事实墙校验",
            "state": "todo"
          },
          {
            "label": "Approval · 人工审批",
            "state": "todo"
          },
          {
            "label": "Export · 导出/发布",
            "state": "todo"
          },
          {
            "label": "Evaluation · 效果评估",
            "state": "todo"
          },
          {
            "label": "Learning · 沉淀 Pattern",
            "state": "todo"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "tabs",
            "id": "sh01",
            "tabs": [
              {
                "label": "创作 Create",
                "sections": [
                  {
                    "type": "form",
                    "title": "Brief / Context（事实来源，非 locale 文案）",
                    "fields": [
                      {
                        "label": "平台",
                        "type": "select",
                        "ph": "",
                        "opts": [
                          "小红书",
                          "抖音",
                          "微博",
                          "微信",
                          "播客"
                        ]
                      },
                      {
                        "label": "创作物类型",
                        "type": "select",
                        "ph": "",
                        "opts": [
                          "文案 Copy",
                          "视觉 Visual",
                          "轮播/海报 Carousel/Poster",
                          "短视频脚本/分镜 Short Video/Storyboard",
                          "Campaign Matrix"
                        ]
                      },
                      {
                        "label": "受众",
                        "type": "input",
                        "ph": "例如：北区高价值会员"
                      },
                      {
                        "label": "目标",
                        "type": "select",
                        "ph": "",
                        "opts": [
                          "种草",
                          "到店转化",
                          "会员复购",
                          "品牌认知"
                        ]
                      },
                      {
                        "label": "语言",
                        "type": "select",
                        "ph": "",
                        "opts": [
                          "简体中文",
                          "English",
                          "한국어（语义本地化，非逐句翻译）"
                        ]
                      }
                    ],
                    "actions": [
                      {
                        "label": "按 Pattern 检索并起草",
                        "variant": "primary",
                        "id": "ai-draft",
                        "cls": "TASK",
                        "scope": "UNKNOWN",
                        "target": "UNKNOWN",
                        "permission": "content:draft",
                        "ico": "orb"
                      },
                      {
                        "label": "保存草稿",
                        "variant": "secondary",
                        "id": "save",
                        "cls": "DRAFT",
                        "scope": "UNKNOWN",
                        "target": "UNKNOWN",
                        "permission": "UNKNOWN",
                        "ico": "check"
                      }
                    ]
                  },
                  {
                    "type": "note",
                    "text": "Scoped Retrieval：只按 Brief/主体/平台/形式/受众/目标/语言/Evidence 检索相关 Pattern，不把整份研究母资产灌进提示词（Contract §6）。",
                    "kind": "RULE",
                    "code": "CC-RETRIEVE"
                  }
                ]
              },
              {
                "label": "素材 Assets",
                "sections": [
                  {
                    "type": "upload",
                    "title": "素材库（上传管线 M12，不制造假进度）",
                    "files": [
                      {
                        "name": "KV_主视觉.png",
                        "pct": 100,
                        "stage": "已入库 · 关联 ASSET-01"
                      },
                      {
                        "name": "门店素材.mp4",
                        "pct": 72,
                        "stage": "转码中 72%"
                      },
                      {
                        "name": "会员日权益口径.pdf",
                        "pct": 100,
                        "stage": "事实源 · BRIEF"
                      }
                    ],
                    "dropTitle": "拖入素材 / 引用 Evidence",
                    "dropHint": null
                  }
                ]
              },
              {
                "label": "成片 Artifacts",
                "sections": [
                  {
                    "type": "cards",
                    "items": [
                      {
                        "title": "春季种草 · 文案 v2",
                        "desc": "Review · 3 处事实已锚定",
                        "ico": "content",
                        "badge": {
                          "text": "待审批",
                          "cls": "warning"
                        },
                        "action": {
                          "label": "打开",
                          "variant": "secondary",
                          "id": "",
                          "cls": "NAVIGATION",
                          "scope": "UNKNOWN",
                          "target": "UNKNOWN",
                          "permission": "UNKNOWN",
                          "size": "sm"
                        }
                      },
                      {
                        "title": "探店短视频脚本+分镜",
                        "desc": "Draft · 故事节拍连续",
                        "ico": "content",
                        "badge": {
                          "text": "草稿",
                          "cls": "brand"
                        }
                      },
                      {
                        "title": "一策略多产物：KV/轮播/口播",
                        "desc": "同一事实核，跨格式复用",
                        "ico": "layers",
                        "badge": {
                          "text": "跨格式",
                          "cls": "success"
                        }
                      },
                      {
                        "title": "会员日 Campaign Matrix",
                        "desc": "决策点/素材矩阵",
                        "ico": "campaign"
                      }
                    ],
                    "cols": 2
                  }
                ]
              }
            ]
          }
        ],
        "side": [
          {
            "type": "ai",
            "title": "AI 协同过程（原型示例，非真实运行结果）",
            "thread": [
              {
                "who": "user",
                "text": "按这份 Brief 与已锚定 Evidence，产出小红书首图文案 3 版。"
              },
              {
                "who": "ai",
                "text": "已生成 3 版（场景/权益/口碑）。每处事实声明均回链 Evidence；无法核实的档期与价格保持 UNKNOWN，未编造。",
                "cites": [
                  "ASSET-01",
                  "EV-B110"
                ],
                "tools": [
                  "pattern.retrieve",
                  "content.draft"
                ]
              }
            ],
            "steps": [
              {
                "label": "INTENT",
                "state": "done"
              },
              {
                "label": "RETRIEVE PATTERN",
                "state": "done"
              },
              {
                "label": "DRAFT",
                "state": "active"
              },
              {
                "label": "FACT WALL",
                "state": ""
              },
              {
                "label": "ARTIFACT",
                "state": ""
              }
            ]
          },
          {
            "type": "note",
            "text": "事实墙 Factuality Wall（§8）：创作自由只针对表达；产品可得性/日期/价格/促销/商户/业绩/引述/平台数据/法务声明必须回链已验证 Evidence 或 Brief 明确给出，否则保持 UNKNOWN 并请求确认。",
            "kind": "RULE",
            "code": "CC-FACT-WALL"
          },
          {
            "type": "table",
            "title": "内容学习 Pattern Registry（§4，结构化学习源，非生产事实）",
            "columns": [
              {
                "label": "Registry",
                "key": "r"
              },
              {
                "label": "承载",
                "key": "d"
              },
              {
                "label": "状态",
                "key": "s",
                "numeric": true,
                "type": "t"
              }
            ],
            "rows": [
              {
                "r": "Narrative 叙事",
                "d": "开场/张力/推进/情绪曲线/证据位/收束",
                "s": "ADOPT",
                "t": "success"
              },
              {
                "r": "Copy 文案",
                "d": "标题逻辑/句式节奏/信息密度/CTA/禁用措辞",
                "s": "ADOPT",
                "t": "success"
              },
              {
                "r": "Visual 视觉",
                "d": "层级/焦点/构图/材质/图文关系/裁剪",
                "s": "EXPERIMENT",
                "t": "warning"
              },
              {
                "r": "Motion/Storyboard",
                "d": "节拍连续性/前后态/静态降级",
                "s": "EXPERIMENT",
                "t": "warning"
              },
              {
                "r": "Campaign 活动",
                "d": "叙事弧/内容矩阵/素材矩阵/决策点/度量",
                "s": "ADOPT",
                "t": "success"
              },
              {
                "r": "Evaluation 评估",
                "d": "事实/品牌契合/原创/平台/可达性 Gate",
                "s": "ADOPT",
                "t": "success"
              }
            ]
          },
          {
            "type": "actions",
            "title": "流转（Review→Approval→Export→Evaluation→Learning）",
            "items": [
              {
                "id": "submit-review",
                "title": "提交评审",
                "icon": "evaluation",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "content:submit",
                "desc": "DRAFT"
              },
              {
                "id": "approve",
                "title": "审批通过",
                "icon": "check",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "content:approve",
                "desc": "EFFECT"
              },
              {
                "id": "publish",
                "title": "发布/导出",
                "icon": "share",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "content:publish",
                "desc": "EFFECT",
                "risk": true
              },
              {
                "id": "promote-learning",
                "title": "评估后沉淀 Pattern",
                "icon": "skill",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "DRAFT"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "ASSET-01",
        "EV-B110",
        "BRIEF"
      ],
      "state_source": "DESIGN_ONLY fixture"
    }
  },
  "SH-02": {
    "titleKey": "screen.SH-02",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Shared · 序境·内容创作",
        "title": "证据库 Evidence Library",
        "titleKey": "screen.SH-02",
        "desc": "统一检索 Source/Evidence/Canonical 引用；每条证据可回溯原始快照与链路。"
      },
      {
        "type": "filters",
        "chips": [
          {
            "label": "全部",
            "on": true
          },
          {
            "label": "Metric",
            "on": false
          },
          {
            "label": "Source",
            "on": false
          },
          {
            "label": "Finding",
            "on": false
          },
          {
            "label": "Risk",
            "on": false
          },
          {
            "label": "Case",
            "on": false
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "table",
            "title": "证据",
            "columns": [
              {
                "label": "ID",
                "key": "id"
              },
              {
                "label": "类型",
                "key": "k"
              },
              {
                "label": "摘要",
                "key": "s"
              },
              {
                "label": "置信",
                "key": "c",
                "numeric": true
              },
              {
                "label": "时间",
                "key": "t"
              },
              {
                "label": "来源",
                "key": "src"
              }
            ],
            "rows": [
              {
                "id": "EV-7701",
                "k": "Metric",
                "s": "今日客流 38,214",
                "c": 99,
                "t": "10:00",
                "src": "footfall"
              },
              {
                "id": "EV-7704",
                "k": "Finding",
                "s": "停车簇 96 条/30.8%",
                "c": 93,
                "t": "09:31",
                "src": "cluster.rule"
              },
              {
                "id": "EV-7710",
                "k": "Risk",
                "s": "停车风险分 72",
                "c": 90,
                "t": "10:22",
                "src": "risk_engine"
              },
              {
                "id": "EV-B110",
                "k": "Source",
                "s": "小红书话题快照",
                "c": 96,
                "t": "09:40",
                "src": "xhs"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "evidence",
            "title": "证据链",
            "items": [
              {
                "kind": "Metric",
                "id": "EV-7701",
                "chain": [
                  "Source",
                  "Canonical",
                  "Metric"
                ],
                "quote": "去重闸机口径，原始快照已固定。",
                "time": "10:00",
                "source": "footfall",
                "conf": 99
              }
            ]
          },
          {
            "type": "actions",
            "title": "证据操作",
            "items": [
              {
                "id": "open-source",
                "title": "查看原始来源",
                "icon": "link",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "NAVIGATION"
              },
              {
                "id": "pin",
                "title": "固定到报告",
                "icon": "report",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "DRAFT"
              }
            ]
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "EV-7701",
        "EV-7704",
        "EV-7710"
      ]
    }
  },
  "SH-03": {
    "titleKey": "screen.SH-03",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Shared · 序境·内容创作",
        "title": "Canonical 数据 / 指标浏览器",
        "titleKey": "screen.SH-03",
        "desc": "浏览 Canonical 表、指标口径与血缘；区分 Canonical 事实与派生指标。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "table",
            "title": "指标目录",
            "columns": [
              {
                "label": "指标",
                "key": "m"
              },
              {
                "label": "口径",
                "key": "d"
              },
              {
                "label": "表",
                "key": "tbl"
              },
              {
                "label": "更新",
                "key": "u"
              },
              {
                "label": "状态",
                "key": "s",
                "numeric": true,
                "type": "t"
              }
            ],
            "rows": [
              {
                "m": "daily_footfall",
                "d": "去重闸机日客流",
                "tbl": "canonical.footfall",
                "u": "1m",
                "s": "OK",
                "t": "success"
              },
              {
                "m": "sentiment_volume",
                "d": "去重平台提及",
                "tbl": "canonical.voice",
                "u": "3m",
                "s": "OK",
                "t": "success"
              },
              {
                "m": "member_sales_share",
                "d": "会员销售/总销售",
                "tbl": "canonical.sales",
                "u": "1h",
                "s": "OK",
                "t": "success"
              },
              {
                "m": "creator_roi",
                "d": "创作者投放 ROI",
                "tbl": "derived",
                "u": "手动",
                "s": "PARTIAL",
                "t": "warning"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "chart",
            "title": "指标血缘（示意）",
            "kind": "line",
            "series": [
              {
                "data": [
                  3,
                  5,
                  8,
                  12,
                  15
                ],
                "color": "var(--lum-c-brand-500)"
              }
            ],
            "labels": [
              "Source",
              "Evidence",
              "Canonical",
              "Metric",
              "VM"
            ]
          },
          {
            "type": "note",
            "text": "Canonical 是唯一事实源；派生指标必须记录计算口径与上游，不允许同名不同义。",
            "kind": "RULE",
            "code": "CANONICAL-ONE"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "DB: canonical"
      ]
    }
  },
  "SH-04": {
    "titleKey": "screen.SH-04",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Shared · 序境·内容创作",
        "title": "报告导出中心",
        "titleKey": "screen.SH-04",
        "desc": "按模板导出 PDF/Excel/PPT，固化口径、时间窗与证据清单；导出动作可审计。",
        "actions": [
          {
            "label": "新建导出",
            "variant": "primary",
            "id": "new-export",
            "cls": "DRAFT",
            "scope": "UNKNOWN",
            "target": "UNKNOWN",
            "permission": "report:export",
            "ico": "download"
          }
        ]
      },
      {
        "type": "split",
        "main": [
          {
            "type": "table",
            "title": "导出任务",
            "columns": [
              {
                "label": "报告",
                "key": "r"
              },
              {
                "label": "格式",
                "key": "f"
              },
              {
                "label": "范围",
                "key": "scope"
              },
              {
                "label": "状态",
                "key": "s",
                "numeric": true,
                "type": "t"
              },
              {
                "label": "证据数",
                "key": "e",
                "numeric": true
              },
              {
                "label": "操作",
                "key": "o"
              }
            ],
            "rows": [
              {
                "r": "运营周报 W37",
                "f": "PDF",
                "scope": "近7天",
                "s": "就绪",
                "t": "success",
                "e": 128,
                "o": "下载"
              },
              {
                "r": "品牌月报",
                "f": "Excel",
                "scope": "近30天",
                "s": "生成中",
                "t": "info",
                "e": 240,
                "o": "—"
              },
              {
                "r": "停车专题",
                "f": "PPT",
                "scope": "自定义",
                "s": "草稿",
                "t": "warning",
                "e": 42,
                "o": "继续"
              }
            ]
          }
        ],
        "side": [
          {
            "type": "upload",
            "title": "导出输入",
            "files": [
              {
                "name": "自定义封面.png",
                "pct": 100,
                "stage": "已附加"
              }
            ],
            "dropTitle": "附加封面/备注",
            "dropHint": null
          },
          {
            "type": "note",
            "text": "导出文件内嵌证据清单与生成时间，保证数字可回溯；原型不真正生成文件。",
            "kind": "RULE",
            "code": "EXPORT-LINEAGE"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "导出固化证据清单"
      ]
    }
  },
  "SH-05": {
    "titleKey": "screen.SH-05",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Shared · 序境·内容创作",
        "title": "学习与评估资产",
        "titleKey": "screen.SH-05",
        "desc": "沉淀 SOP、复盘、培训与评估题库，区分已验证资产与草稿。"
      },
      {
        "type": "cards",
        "items": [
          {
            "title": "高峰疏导 SOP",
            "desc": "已验证 · 来自 CASE-221",
            "ico": "folder",
            "badge": {
              "text": "已验证",
              "cls": "success"
            }
          },
          {
            "title": "活动保障 Checklist",
            "desc": "跨部门清单",
            "ico": "folder"
          },
          {
            "title": "AI 提示词库",
            "desc": "按能力分类的可复用 Prompt",
            "ico": "skill"
          },
          {
            "title": "评估题库",
            "desc": "验收/回归用例",
            "ico": "evaluation",
            "badge": {
              "text": "128 题",
              "cls": "brand"
            }
          },
          {
            "title": "历史复盘",
            "desc": "按 Campaign/事件归档",
            "ico": "case"
          },
          {
            "title": "培训材料",
            "desc": "新人上手路径",
            "ico": "content"
          }
        ],
        "cols": 3
      },
      {
        "type": "table",
        "title": "最近更新",
        "columns": [
          {
            "label": "资产",
            "key": "a"
          },
          {
            "label": "类型",
            "key": "t"
          },
          {
            "label": "验证",
            "key": "v",
            "numeric": true,
            "type": "vt"
          },
          {
            "label": "更新",
            "key": "u"
          }
        ],
        "rows": [
          {
            "a": "高峰疏导 SOP",
            "t": "SOP",
            "v": "已验证",
            "vt": "success",
            "u": "09-10"
          },
          {
            "a": "KOC 脚本模板",
            "t": "Prompt",
            "v": "待验证",
            "vt": "warning",
            "u": "09-08"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "资产来源 Case/Report"
      ]
    }
  },
  "SH-06": {
    "titleKey": "screen.SH-06",
    "sections": [
      {
        "type": "head",
        "eyebrow": "Shared · 序境·内容创作",
        "title": "通知 / 任务中心",
        "titleKey": "screen.SH-06",
        "desc": "聚合待办、审批、告警与订阅；区分需要行动与仅知会。"
      },
      {
        "type": "split",
        "main": [
          {
            "type": "tabs",
            "id": "sh06",
            "tabs": [
              {
                "label": "待办",
                "sections": [
                  {
                    "type": "table",
                    "title": "",
                    "columns": [
                      {
                        "label": "任务",
                        "key": "t"
                      },
                      {
                        "label": "来源",
                        "key": "s"
                      },
                      {
                        "label": "优先级",
                        "key": "p",
                        "numeric": true,
                        "type": "pt"
                      },
                      {
                        "label": "截止",
                        "key": "d"
                      }
                    ],
                    "rows": [
                      {
                        "t": "审批：门店探店成片",
                        "s": "内容中心",
                        "p": "高",
                        "pt": "danger",
                        "d": "今天"
                      },
                      {
                        "t": "确认周报 W37",
                        "s": "报告",
                        "p": "中",
                        "pt": "warning",
                        "d": "明天"
                      },
                      {
                        "t": "处置 Case-221",
                        "s": "风险中心",
                        "p": "高",
                        "pt": "danger",
                        "d": "今天"
                      }
                    ]
                  }
                ]
              },
              {
                "label": "通知",
                "sections": [
                  {
                    "type": "events",
                    "title": "",
                    "items": [
                      {
                        "time": "10:22",
                        "title": "停车风险升高",
                        "desc": "风险分 72",
                        "date": "",
                        "level": "high",
                        "tags": [],
                        "evidence": "EV-7710"
                      },
                      {
                        "time": "09:40",
                        "title": "导出就绪",
                        "desc": "运营周报 PDF",
                        "date": "",
                        "level": "low",
                        "tags": [],
                        "evidence": ""
                      }
                    ],
                    "more": true
                  }
                ]
              },
              {
                "label": "告警",
                "sections": [
                  {
                    "type": "runtime",
                    "title": "系统告警",
                    "items": [
                      {
                        "name": "采集器退避",
                        "state": "warn",
                        "detail": "点评限流"
                      },
                      {
                        "name": "AI 超时已降级",
                        "state": "ok",
                        "detail": "本地兜底"
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ],
        "side": [
          {
            "type": "actions",
            "title": "快速处理",
            "items": [
              {
                "id": "approve",
                "title": "通过审批",
                "icon": "check",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "approval:write",
                "desc": "EFFECT",
                "risk": true
              },
              {
                "id": "snooze",
                "title": "稍后提醒",
                "icon": "clock",
                "cls": "NAVIGATION",
                "scope": "UNKNOWN",
                "target": "UNKNOWN",
                "permission": "UNKNOWN",
                "desc": "DRAFT"
              }
            ]
          },
          {
            "type": "note",
            "text": "EFFECT 类处理（通过/驳回/指派）弹确认并走后端权限；原型仅演示。",
            "kind": "RULE",
            "code": "NOTIF-EFFECT"
          }
        ]
      }
    ],
    "context": {
      "evidence": [
        "待办来源各域"
      ]
    }
  }
};
