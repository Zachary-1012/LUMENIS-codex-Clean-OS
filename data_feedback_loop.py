"""
数据闭环引擎 v1.0
5层闭环架构 - 第三层：数据闭环
功能：
正向流程（已有）：
  采集 → 清洗 → 主体过滤 → 去重 → 入库 → 事件聚合 → 风险识别 → 舆情分析 → 报告 → 推送

反向反馈（新增）：
  报告结果
    ↓
  发现异常（负面突增/某品牌投诉集中/某时段数据缺失）
    ↓
  反馈给采集/规则层
    ↓
  调整策略（增加该品牌关键词/调整采集时段/优化过滤规则）
    ↓
  下一轮采集验证效果

不需要登录，本地运行即可
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from collections import Counter

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class DataFeedbackLoop:
    """数据闭环引擎"""

    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(self.root_dir, 'data', 'monitor.db')
        self.feedback_file = os.path.join(self.root_dir, 'data', 'feedback_loop.json')
        self.suggestions_file = os.path.join(self.root_dir, 'data', 'strategy_suggestions.json')

        # 加载反馈历史
        self.feedback_history = self._load_feedback()

    def _load_feedback(self):
        """加载反馈历史"""
        try:
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_feedback(self):
        """保存反馈历史"""
        try:
            # 只保留最近100条
            self.feedback_history = self.feedback_history[-100:]
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DataFeedback] 保存反馈失败: {e}", flush=True)

    def _get_db_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path, timeout=10)

    def analyze_report_anomalies(self, date_str=None):
        """分析报告异常，发现需要反馈的问题"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        anomalies = []

        try:
            conn = self._get_db_connection()
            c = conn.cursor()

            # 1. 检测负面舆情突增
            try:
                # 当天负面数量
                c.execute("""
                    SELECT COUNT(*) FROM notes 
                    WHERE sentiment='negative' 
                    AND date(collected_at)=?
                """, (date_str,))
                today_negative = c.fetchone()[0]

                # 过去7天平均负面数量
                c.execute("""
                    SELECT AVG(daily_count) FROM (
                        SELECT COUNT(*) as daily_count 
                        FROM notes 
                        WHERE sentiment='negative' 
                        AND date(collected_at) >= date(?, '-7 days')
                        AND date(collected_at) < ?
                        GROUP BY date(collected_at)
                    )
                """, (date_str, date_str))
                avg_negative = c.fetchone()[0] or 0

                if today_negative > 0 and avg_negative > 0:
                    increase_ratio = today_negative / avg_negative
                    if increase_ratio > 2.0:
                        anomalies.append({
                            'type': 'negative_surge',
                            'severity': 'high' if increase_ratio > 3 else 'medium',
                            'description': f'负面舆情突增，当天{today_negative}条，7天平均{avg_negative:.1f}条，增长{increase_ratio:.1f}倍',
                            'suggestion': '建议增加相关关键词采集，重点关注负面事件发展',
                            'data': {'today': today_negative, 'avg_7d': avg_negative, 'ratio': increase_ratio}
                        })
            except Exception as e:
                print(f"[DataFeedback] 检测负面突增失败: {e}", flush=True)

            # 2. 检测某品牌投诉集中
            try:
                # 先检查是否有brand列
                c.execute("PRAGMA table_info(notes)")
                columns = [row[1] for row in c.fetchall()]
                if 'brand' in columns:
                    c.execute("""
                        SELECT brand, COUNT(*) as cnt 
                        FROM notes 
                        WHERE sentiment='negative' 
                        AND date(collected_at)=?
                        AND brand IS NOT NULL AND brand != ''
                        GROUP BY brand 
                        ORDER BY cnt DESC 
                        LIMIT 5
                    """, (date_str,))
                    brand_negatives = c.fetchall()

                    for brand, count in brand_negatives:
                        if count >= 3:
                            anomalies.append({
                                'type': 'brand_complaint_cluster',
                                'severity': 'high' if count >= 5 else 'medium',
                                'description': f'品牌"{brand}"投诉集中，当天{count}条负面',
                                'suggestion': f'建议增加"{brand}"相关关键词采集，关注该品牌舆情发展',
                                'data': {'brand': brand, 'count': count}
                            })
            except Exception as e:
                print(f"[DataFeedback] 检测品牌投诉集中失败: {e}", flush=True)

            # 3. 检测某时段数据缺失
            try:
                c.execute("""
                    SELECT strftime('%H', collected_at) as hour, COUNT(*) as cnt
                    FROM notes
                    WHERE date(collected_at)=?
                    GROUP BY hour
                    ORDER BY hour
                """, (date_str,))
                hourly_data = {row[0]: row[1] for row in c.fetchall()}

                # 检查自动采集时段（8,10,12,14,16,18,20,22,23点）
                auto_hours = ['08', '10', '12', '14', '16', '18', '20', '22', '23']
                current_hour = datetime.now().strftime('%H')

                missing_hours = []
                for h in auto_hours:
                    if h < current_hour and h not in hourly_data:
                        missing_hours.append(h)

                if missing_hours:
                    anomalies.append({
                        'type': 'data_missing',
                        'severity': 'medium',
                        'description': f'时段数据缺失，缺失时段: {", ".join(missing_hours)}点',
                        'suggestion': '建议检查采集器是否正常运行，补充缺失时段数据',
                        'data': {'missing_hours': missing_hours}
                    })
            except Exception as e:
                print(f"[DataFeedback] 检测时段数据缺失失败: {e}", flush=True)

            # 4. 检测正面/负面比例异常
            try:
                c.execute("""
                    SELECT sentiment, COUNT(*) FROM notes 
                    WHERE date(collected_at)=?
                    GROUP BY sentiment
                """, (date_str,))
                sentiment_dist = {row[0]: row[1] for row in c.fetchall()}

                total = sum(sentiment_dist.values())
                if total > 0:
                    negative_ratio = sentiment_dist.get('negative', 0) / total
                    if negative_ratio > 0.5:
                        anomalies.append({
                            'type': 'sentiment_imbalance',
                            'severity': 'medium',
                            'description': f'舆情情绪失衡，负面占比{negative_ratio*100:.1f}%',
                            'suggestion': '建议关注整体舆情走向，是否有重大负面事件',
                            'data': {'negative_ratio': negative_ratio, 'distribution': sentiment_dist}
                        })
            except Exception as e:
                print(f"[DataFeedback] 检测情绪比例异常失败: {e}", flush=True)

            # 5. 检测去重率异常（可能采集到大量重复内容）
            try:
                c.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at)=?", (date_str,))
                today_total = c.fetchone()[0]
                c.execute("SELECT COUNT(DISTINCT note_id) FROM notes WHERE date(collected_at)=?", (date_str,))
                today_unique = c.fetchone()[0]

                if today_total > 0:
                    dup_rate = 1 - (today_unique / today_total)
                    if dup_rate > 0.3:
                        anomalies.append({
                            'type': 'high_duplicate_rate',
                            'severity': 'low',
                            'description': f'去重率异常，重复率{dup_rate*100:.1f}%',
                            'suggestion': '建议优化去重规则，检查采集关键词是否过于宽泛',
                            'data': {'total': today_total, 'unique': today_unique, 'dup_rate': dup_rate}
                        })
            except Exception as e:
                print(f"[DataFeedback] 检测去重率异常失败: {e}", flush=True)

            conn.close()

        except Exception as e:
            print(f"[DataFeedback] 分析报告异常失败: {e}", flush=True)

        return anomalies

    def generate_strategy_suggestions(self, anomalies):
        """根据异常生成策略建议"""
        suggestions = []

        for anomaly in anomalies:
            suggestion = {
                'anomaly_type': anomaly['type'],
                'severity': anomaly['severity'],
                'description': anomaly['description'],
                'suggestion': anomaly['suggestion'],
                'action_items': [],
                'priority': 'high' if anomaly['severity'] == 'high' else 'medium'
            }

            # 根据异常类型生成具体行动项
            if anomaly['type'] == 'negative_surge':
                suggestion['action_items'] = [
                    '增加负面事件相关关键词到采集列表',
                    '缩短该事件相关内容的采集间隔',
                    '触发事件聚合分析，识别是否为同一事件',
                    '生成专报提醒'
                ]
            elif anomaly['type'] == 'brand_complaint_cluster':
                brand = anomaly['data'].get('brand', '')
                suggestion['action_items'] = [
                    f'增加"{brand}"品牌相关关键词',
                    f'重点采集"{brand}"的投诉内容',
                    f'分析"{brand}"投诉的共性问题',
                    f'生成品牌舆情专报'
                ]
            elif anomaly['type'] == 'data_missing':
                suggestion['action_items'] = [
                    '检查采集器运行状态',
                    '检查CDP浏览器是否正常',
                    '检查登录态是否有效',
                    '手动触发补充采集'
                ]
            elif anomaly['type'] == 'sentiment_imbalance':
                suggestion['action_items'] = [
                    '识别是否有重大负面事件',
                    '增加正面内容采集权重',
                    '分析负面内容的传播路径',
                    '生成舆情预警'
                ]
            elif anomaly['type'] == 'high_duplicate_rate':
                suggestion['action_items'] = [
                    '优化去重规则（增加内容相似度判断）',
                    '检查采集关键词是否过于宽泛',
                    '增加品牌/业态维度的过滤',
                    '清理重复数据'
                ]

            suggestions.append(suggestion)

        return suggestions

    def apply_feedback(self, suggestions):
        """应用反馈到采集/规则层"""
        applied = []

        for suggestion in suggestions:
            # 记录反馈
            feedback_entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'anomaly_type': suggestion['anomaly_type'],
                'severity': suggestion['severity'],
                'description': suggestion['description'],
                'suggestion': suggestion['suggestion'],
                'action_items': suggestion['action_items'],
                'priority': suggestion['priority'],
                'status': 'pending',  # pending/applied/ignored
                'applied_at': None
            }

            self.feedback_history.append(feedback_entry)
            applied.append(feedback_entry)

        # 保存
        self._save_feedback()

        # 保存策略建议
        try:
            with open(self.suggestions_file, 'w', encoding='utf-8') as f:
                json.dump(suggestions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DataFeedback] 保存策略建议失败: {e}", flush=True)

        return applied

    def run_feedback_cycle(self, date_str=None):
        """运行一次完整的反馈周期"""
        print("[DataFeedback] 开始数据反馈周期...", flush=True)

        # 1. 分析报告异常
        anomalies = self.analyze_report_anomalies(date_str)
        print(f"[DataFeedback] 发现 {len(anomalies)} 个异常", flush=True)

        if not anomalies:
            print("[DataFeedback] 无异常，无需反馈", flush=True)
            return {'status': 'no_anomalies', 'anomalies': [], 'suggestions': []}

        # 2. 生成策略建议
        suggestions = self.generate_strategy_suggestions(anomalies)
        print(f"[DataFeedback] 生成 {len(suggestions)} 条策略建议", flush=True)

        # 3. 应用反馈
        applied = self.apply_feedback(suggestions)
        print(f"[DataFeedback] 已记录 {len(applied)} 条反馈", flush=True)

        return {
            'status': 'feedback_applied',
            'anomalies': anomalies,
            'suggestions': suggestions,
            'applied_count': len(applied)
        }

    def get_feedback_history(self, limit=20):
        """获取反馈历史"""
        return self.feedback_history[-limit:]

    def get_pending_feedback(self):
        """获取待处理的反馈"""
        return [f for f in self.feedback_history if f.get('status') == 'pending']

    def mark_feedback_applied(self, feedback_index):
        """标记反馈为已应用"""
        if 0 <= feedback_index < len(self.feedback_history):
            self.feedback_history[feedback_index]['status'] = 'applied'
            self.feedback_history[feedback_index]['applied_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_feedback()
            return True
        return False

    def get_stats(self):
        """获取统计信息"""
        total = len(self.feedback_history)
        pending = len([f for f in self.feedback_history if f.get('status') == 'pending'])
        applied = len([f for f in self.feedback_history if f.get('status') == 'applied'])
        high_severity = len([f for f in self.feedback_history if f.get('severity') == 'high'])

        return {
            'total_feedback': total,
            'pending': pending,
            'applied': applied,
            'high_severity': high_severity,
            'last_feedback': self.feedback_history[-1]['timestamp'] if self.feedback_history else None
        }


# 全局实例
data_feedback_loop = DataFeedbackLoop()

print("[DataFeedback] 数据闭环引擎已加载", flush=True)
