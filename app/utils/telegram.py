import requests
import logging
from app.models import SystemConfig

class TelegramNotifier:
    """Telegram通知工具类"""
    
    @staticmethod
    def send_message(message):
        """
        发送消息到Telegram
        
        参数:
            message: 要发送的消息文本
        
        返回:
            bool: 发送是否成功
        """
        # 获取Telegram机器人配置
        bot_token = SystemConfig.get_value('telegram_bot_token', '')
        chat_id = SystemConfig.get_value('telegram_chat_id', '')
        
        # 如果未配置，则不发送
        if not bot_token or not chat_id:
            logging.warning("Telegram机器人未配置，无法发送通知")
            return False
        
        try:
            # 发送消息
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data)
            
            # 检查响应
            if response.status_code == 200:
                logging.info(f"Telegram通知发送成功: {message[:50]}...")
                return True
            else:
                logging.error(f"Telegram通知发送失败: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Telegram通知发送异常: {str(e)}")
            return False
    
    @staticmethod
    def send_order_notification(order):
        """
        发送订单创建通知
        
        参数:
            order: 订单对象
        
        返回:
            bool: 发送是否成功
        """
        # 检查是否启用订单通知
        if SystemConfig.get_value('enable_order_notification', 'False') != 'True':
            return False
        
        # 添加详细日志，帮助诊断问题
        logging.info(f"订单ID: {order.id}, 订单号: {order.order_id}, user_id: {order.user_id}, email: {order.email}")
        
        # 判断下单类型 - 使用更严格的判断
        is_anonymous = order.user_id is None
        order_type = "👤 登录用户" if not is_anonymous else "🕶️ 匿名下单"
        
        logging.info(f"订单类型判断: is_anonymous={is_anonymous}, order_type={order_type}")
        
        # 构建消息
        message = f"<b>🛍️ 新订单通知 #{order.id}</b>\n\n"
        message += f"📋 <b>订单信息</b>\n"
        message += f"━━━━━━━━━━━━━━━\n"
        message += f"🔢 订单号: <code>{order.order_id}</code>\n"
        message += f"🏷️ 商品: <b>{order.product.name}</b>\n"
        message += f"🔢 数量: <b>{order.quantity}</b>\n"
        message += f"💰 金额: <b>¥{order.total_price}</b>\n"
        message += f"⏱️ 时间: {order.create_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"📊 类型: <b>{order_type}</b>\n"
        
        if order.email:
            message += f"📧 邮箱: {order.email}\n"
        
        message += f"\n💡 <i>请及时处理订单</i>"
        
        # 发送消息
        return TelegramNotifier.send_message(message)
    
    @staticmethod
    def send_payment_notification(order):
        """
        发送支付成功通知
        
        参数:
            order: 订单对象
        
        返回:
            bool: 发送是否成功
        """
        # 检查是否启用支付通知
        if SystemConfig.get_value('enable_payment_notification', 'False') != 'True':
            return False
        
        # 添加详细日志，帮助诊断问题
        logging.info(f"支付通知 - 订单ID: {order.id}, 订单号: {order.order_id}, user_id: {order.user_id}, email: {order.email}")
        
        # 判断下单类型 - 使用更严格的判断
        is_anonymous = order.user_id is None
        order_type = "👤 登录用户" if not is_anonymous else "🕶️ 匿名下单"
        
        logging.info(f"订单类型判断: is_anonymous={is_anonymous}, order_type={order_type}")
        
        # 构建消息
        message = f"<b>💸 支付成功通知 #{order.id}</b>\n\n"
        message += f"📋 <b>订单信息</b>\n"
        message += f"━━━━━━━━━━━━━━━\n"
        message += f"🔢 订单号: <code>{order.order_id}</code>\n"
        message += f"🏷️ 商品: <b>{order.product.name}</b>\n"
        message += f"🔢 数量: <b>{order.quantity}</b>\n"
        message += f"💰 金额: <b>¥{order.total_price}</b>\n"
        message += f"⏱️ 支付时间: {order.pay_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"📊 类型: <b>{order_type}</b>\n"
        
        if order.email:
            message += f"📧 邮箱: {order.email}\n"
            
        message += f"\n✅ <i>订单已完成支付</i>"
        
        # 发送消息
        return TelegramNotifier.send_message(message) 