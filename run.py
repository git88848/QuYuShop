from app import create_app
from app.tasks import start_scheduler

app = create_app()

# 启动订单过期处理定时任务
scheduler_thread = start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False) 