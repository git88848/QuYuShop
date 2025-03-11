import time
import threading
import logging
from datetime import datetime
from app import create_app, db
from app.models import Order, SystemConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('order_tasks')

# 全局变量，用于跟踪定时任务是否已启动
_scheduler_thread = None
_scheduler_running = False

def handle_expired_orders():
    """处理过期订单的任务"""
    try:
        # 查找所有已过期但状态仍为未支付的订单
        current_time = datetime.now()
        expired_orders = Order.query.filter(
            Order.status == 0,
            Order.expire_time < current_time
        ).all()
        
        if not expired_orders:
            logger.info("没有需要处理的过期订单")
            return {"count": 0, "message": "没有需要处理的过期订单"}
        
        count = len(expired_orders)
        logger.info(f"找到 {count} 个过期订单需要处理")
        
        # 更新订单状态为已过期
        for order in expired_orders:
            order.status = -2
            logger.info(f"订单 {order.order_id} 已过期，状态已更新")
        
        db.session.commit()
        logger.info("所有过期订单处理完成")
        
        return {
            "count": count,
            "message": f"成功处理 {count} 个过期订单"
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"处理过期订单时出错: {str(e)}")
        raise

def run_scheduler():
    """运行定时任务调度器"""
    global _scheduler_running
    
    logger.info("订单过期处理定时任务已启动")
    app = create_app()
    
    while _scheduler_running:
        try:
            with app.app_context():
                # 获取配置的检查间隔（默认60秒）
                check_interval = int(SystemConfig.get_value('order_check_interval', '60'))
                
                # 检查过期订单
                handle_expired_orders()
                
                # 使用配置的间隔时间
                logger.info(f"下次检查将在 {check_interval} 秒后进行")
            
            # 等待指定的时间间隔
            time.sleep(check_interval)
        except Exception as e:
            logger.error(f"定时任务执行出错: {str(e)}")
            # 出错后等待一段时间再继续
            time.sleep(30)
    
    logger.info("订单过期处理定时任务已停止")

def start_scheduler():
    """在后台线程中启动定时任务调度器"""
    global _scheduler_thread, _scheduler_running
    
    # 如果定时任务已经在运行，则不再启动新的任务
    if _scheduler_running and _scheduler_thread and _scheduler_thread.is_alive():
        logger.info("订单过期处理定时任务已在运行中，不再重复启动")
        return _scheduler_thread
    
    # 设置运行标志
    _scheduler_running = True
    
    # 创建并启动线程
    _scheduler_thread = threading.Thread(target=run_scheduler)
    _scheduler_thread.daemon = True
    _scheduler_thread.start()
    
    return _scheduler_thread

def stop_scheduler():
    """停止定时任务"""
    global _scheduler_running, _scheduler_thread
    
    if _scheduler_running and _scheduler_thread:
        logger.info("正在停止订单过期处理定时任务...")
        _scheduler_running = False
        
        # 等待线程结束
        if _scheduler_thread.is_alive():
            _scheduler_thread.join(timeout=5)
            
        logger.info("订单过期处理定时任务已停止")
        return True
    
    return False 