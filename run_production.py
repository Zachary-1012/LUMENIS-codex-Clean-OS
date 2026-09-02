# ============================================================
# Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
#  此入口已标注为 LEGACY（保留用于调试/历史兼容）。官方统一生产入口已收敛为：
#     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#  如确需直接执行此 .py，请使用项目 .venv：  .venv\Scripts\python.exe <this_file>.py
# ============================================================
"""
广州太古汇舆情监测系统 - 生产级WSGI服务器
使用waitress作为生产级WSGI服务器（Windows推荐）
比Flask开发服务器更稳定、更高效、支持更多并发

参考GitHub实际应用：
- bmosoluciones/flask-starter: waitress部署
- lokeshbhure011/lokesh-url-shortener: 生产级部署

备选方案：
- gunicorn (Linux推荐，Windows不支持)
- uWSGI (高性能，配置复杂)
- tornado (异步，适合高并发)
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))

# 导入Flask应用
from app import app

def main():
    parser = argparse.ArgumentParser(description='广州太古汇舆情监测系统 - 生产级服务器')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址（默认: 0.0.0.0）')
    parser.add_argument('--port', type=int, default=8200, help='监听端口（默认: 8200）')
    parser.add_argument('--threads', type=int, default=8, help='工作线程数（默认: 8）')
    parser.add_argument('--backlog', type=int, default=2048, help='连接队列大小（默认: 2048）')
    parser.add_argument('--no-auth', action='store_true', help='禁用HTTP认证（仅本机访问时使用）')
    args = parser.parse_args()
    
    # 设置环境变量
    if args.no_auth:
        os.environ['DISABLE_AUTH'] = '1'
    
    print('=' * 60)
    print('广州太古汇舆情监测系统 - 生产级服务器 (waitress)')
    print('=' * 60)
    print(f'监听地址: http://{args.host}:{args.port}')
    print(f'工作线程: {args.threads}')
    print(f'连接队列: {args.backlog}')
    print(f'HTTP认证: {"关闭" if args.no_auth else "开启"}')
    print('=' * 60)
    print()
    
    try:
        from waitress import serve
        
        # ===== 在启动waitress之前，先执行app.py中的启动代码 =====
        print('[Init] 启动后台服务...')
        
        # 1. 启动调度器（崩溃根因[重复endpoint]已修复，恢复自动采集/日报/周报/邮件的自动运行）
        try:
            import threading
            from app import scheduler_loop, _weekly_scheduler
            threading.Thread(target=scheduler_loop, daemon=True, name='scheduler').start()
            try:
                threading.Thread(target=_weekly_scheduler, daemon=True, name='weekly_scheduler').start()
            except Exception as we:
                print(f'[Scheduler] 周报调度器未启动: {we}')
            print('[Scheduler] 自动采集/日报调度器已启动')
        except Exception as e:
            print(f'[Scheduler] 启动失败: {e}')
        
        # 2. 启动内存监控（崩溃根因[重复endpoint]已修复，恢复OOM防护）
        try:
            from memory_optimizer import get_memory_optimizer
            mem_opt = get_memory_optimizer()
            mem_opt.start_monitoring()
            print('[Memory] 内存监控已启动')
        except Exception as e:
            print(f'[Memory] 启动失败: {e}')
        
        # 3. 启动稳定性监控（watchdog+heartbeat，仅记录不强制退出）
        try:
            from stability_monitor import get_stability_monitor
            stab_mon = get_stability_monitor()
            stab_mon.start_monitoring()
            print('[Stability] 稳定性监控已启动（watchdog+heartbeat）')
        except Exception as e:
            print(f'[Stability] 启动失败: {e}')
        
        # 4. 检查CDP浏览器状态（不自动启动，避免崩溃）
        try:
            import cdp_helper
            cdp_status = cdp_helper.get_cdp_status()
            if cdp_status.get('available'):
                print(f'[CDP] 浏览器已就绪: 端口 {cdp_status.get("port")}')
            else:
                print('[CDP] 浏览器未启动，采集时将按需自动启动（避免启动时崩溃）')
        except Exception as e:
            print(f'[CDP] 检查失败: {e}')
        
        print('[Init] 后台服务启动完成')
        print()
        
        # waitress生产级配置
        serve(
            app,
            host=args.host,
            port=args.port,
            threads=args.threads,
            backlog=args.backlog,
            ident='TaikooMonitor/5.8.9',
            # 性能优化
            max_request_body_size=1073741824,  # 1GB
            outbuf_overflow=1048576,  # 1MB
            inbuf_overflow=524288,  # 512KB
            connection_limit=1000,
            cleanup_interval=30,
            channel_timeout=120,
        )
        
    except ImportError:
        print('❌ waitress未安装，回退到Flask开发服务器')
        print('   安装命令: pip install waitress')
        print()
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    
    except KeyboardInterrupt:
        print('\n服务器已停止')
        sys.exit(0)
    
    except Exception as e:
        print(f'❌ 服务器启动失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
