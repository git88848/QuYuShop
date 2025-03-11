import os
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from markupsafe import Markup
from datetime import timedelta
import time

# 加载环境变量
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
bootstrap = Bootstrap()

# 全局变量，用于跟踪应用是否已初始化过定时任务
_scheduler_initialized = False

# 用于存储访问记录的内存缓存
_page_view_cache = {}

def cleanup_expired_cache():
    """清理过期的缓存记录"""
    current_time = time.time()
    expired_keys = [k for k, v in _page_view_cache.items() if current_time - v > 300]  # 5分钟过期
    for k in expired_keys:
        del _page_view_cache[k]

def create_app():
    global _scheduler_initialized
    
    app = Flask(__name__)
    
    # 配置应用
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    
    # 检查数据库配置
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError('DATABASE_URL environment variable is not set')
    if database_url.startswith('sqlite'):
        raise ValueError('SQLite is not supported, please use MySQL')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
    
    # 确保上传目录存在
    upload_dir = os.path.join(app.root_path, 'static', app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    db.init_app(app)
    login_manager.init_app(app)
    bootstrap.init_app(app)
    
    # 注册蓝图
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    # 注入当前时间到模板
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # 注入站点信息到模板
    @app.context_processor
    def inject_site_info():
        from .models import SystemConfig
        from flask import request
        
        # 获取系统配置
        site_name = SystemConfig.get_value('site_name', '趋于自助商城系统')
        site_title = SystemConfig.get_value('site_title', '趋于自助商城系统')
        site_description = SystemConfig.get_value('site_description', '趋于自助商城系统，人人都可拥有自己的独立商城')
        site_keywords = SystemConfig.get_value('site_keywords', '趋于自助商城系统')
        # 从请求中自动获取网站域名
        site_url = SystemConfig.get_value('site_url', request.host_url.rstrip('/'))
        site_logo = SystemConfig.get_value('site_logo', '/static/img/logo.png')
        site_favicon = SystemConfig.get_value('site_favicon', '/static/img/favicon.ico')
        
        # 页脚信息
        footer_text = SystemConfig.get_value('footer_text', '© 2025 趋于自助商城系统')
        footer_link = SystemConfig.get_value('footer_link', 'https://github.com/git88848')
        about_us = SystemConfig.get_value('about_us', '趋于自助商城系统，人人都可拥有自己的独立商城')
        
        # 联系方式
        contact_email = SystemConfig.get_value('contact_email', 'admin@example.com')
        contact_phone = SystemConfig.get_value('contact_phone', '(907) 793-9460')
        
        # 微信设置
        site_weixin = SystemConfig.get_value('site_weixin', 'weixin888')
        show_weixin = SystemConfig.get_value('show_weixin', '0') == str(1)  # 默认不显示
        
        # Telegram 信息
        telegram_username = SystemConfig.get_value('telegram_username', 'Lawofforce')
        telegram_channel = SystemConfig.get_value('telegram_channel', 'QUYUkjpd')
        telegram_group = SystemConfig.get_value('telegram_group', 'QUYUkjq')
        
        # 显示控制
        show_email = SystemConfig.get_value('show_email', '0') == str(1)
        show_phone = SystemConfig.get_value('show_phone', '0') == str(1)
        show_telegram_username = SystemConfig.get_value('show_telegram_username', '1') == str(1)
        show_telegram_channel = SystemConfig.get_value('show_telegram_channel', '1') == str(1)
        show_telegram_group = SystemConfig.get_value('show_telegram_group', '1') == str(1)
        
        # Telegram机器人设置
        telegram_bot_token = SystemConfig.get_value('telegram_bot_token', '7175153476:AAHHtjZ9P_8u0BzQTkeQBJFCY4hLhBSKCRE')
        telegram_chat_id = SystemConfig.get_value('telegram_chat_id', '-1001923404194')
        enable_telegram_notify = SystemConfig.get_value('enable_telegram_notify', '1') == str(1)
        
        # 验证码配置
        enable_captcha = SystemConfig.get_value('enable_captcha', '1') == str(1)
        
        return dict(
            site_name=site_name,
            site_title=site_title,
            site_description=site_description,
            site_keywords=site_keywords,
            site_url=site_url,
            site_logo=site_logo,
            site_favicon=site_favicon,
            footer_text=footer_text,
            footer_link=footer_link,
            about_us=about_us,
            contact_email=contact_email,
            contact_phone=contact_phone,
            site_weixin=site_weixin,
            show_weixin=show_weixin,
            telegram_username=telegram_username,
            telegram_channel=telegram_channel,
            telegram_group=telegram_group,
            show_email=show_email,
            show_phone=show_phone,
            show_telegram_username=show_telegram_username,
            show_telegram_channel=show_telegram_channel,
            show_telegram_group=show_telegram_group,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            enable_telegram_notify=enable_telegram_notify,
            enable_captcha=enable_captcha
        )
    
    # 添加自定义过滤器
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s:
            return Markup(s.replace('\n', '<br>'))
        return s
    
    # 添加请求钩子，记录页面访问统计
    @app.before_request
    def before_request():
        from flask import request, g
        from flask_login import current_user
        from .models import PageView, db
        import datetime
        
        # 排除静态文件、API路由、后台页面和管理员访问
        if (not request.path.startswith('/static') and 
            not request.path.startswith('/api') and 
            not request.path.startswith('/admin') and 
            request.method == 'GET' and
            (current_user.is_anonymous or not current_user.is_admin)):  # 排除管理员访问
            
            # 清理过期缓存
            cleanup_expired_cache()
            
            # 使用内存缓存进行IP访问限制
            # 获取真实的用户IP，优先使用X-Forwarded-For或X-Real-IP头
            if request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            elif request.headers.get('X-Real-IP'):
                ip = request.headers.get('X-Real-IP')
            else:
                # 在开发环境中，如果是本地IP（127.0.0.1或localhost），则使用一个模拟的外部IP
                if request.remote_addr in ['127.0.0.1', 'localhost', '::1'] or request.remote_addr.startswith('192.168.') or request.remote_addr.startswith('26.26.'):
                    ip = '114.114.114.114'  # 使用一个模拟的外部IP
                else:
                    ip = request.remote_addr
            
            path = request.path
            cache_key = f"{ip}:{path}"
            current_time = time.time()
            
            # 检查是否是同一IP在5分钟内的重复访问
            if cache_key not in _page_view_cache:
                # 记录访问
                page_view = PageView(
                    path=path,
                    ip=ip,
                    user_agent=request.user_agent.string,
                    referer=request.referrer,
                    user_id=current_user.id if not current_user.is_anonymous else None,
                    created_at=datetime.datetime.utcnow()
                )
                db.session.add(page_view)
                db.session.commit()
                
                # 更新缓存
                _page_view_cache[cache_key] = current_time
    
    # 启动订单过期处理定时任务（仅在应用启动时执行一次）
    if not _scheduler_initialized:
        with app.app_context():
            # 导入放在这里避免循环导入
            from app.tasks.order_tasks import start_scheduler, stop_scheduler
            
            # 先尝试停止已有的定时任务
            stop_scheduler()
            
            # 启动新的定时任务
            start_scheduler()
            
            # 标记为已初始化
            _scheduler_initialized = True
    
    return app 