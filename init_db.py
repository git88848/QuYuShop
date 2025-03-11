#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import hashlib
from datetime import datetime
from dotenv import load_dotenv
from app import create_app, db
from app.models import User, Category, Product, Card, Order, EpayConfig, SystemConfig
from werkzeug.security import generate_password_hash

# 加载环境变量
load_dotenv()

def init_db():
    """初始化数据库"""
    # 添加用户确认提示
    confirm = input("警告：这将删除所有现有数据！是否继续？(y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return

    app = create_app()
    with app.app_context():
        print("开始初始化数据库...")
        
        # 删除所有现有数据
        print("正在删除现有数据...")
        db.drop_all()
        
        # 创建所有表
        db.create_all()
        print("所有表已创建")
        
        # 检查是否已存在管理员用户
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            # 创建管理员用户
            admin = User(
                username=os.getenv('ADMIN_USERNAME', 'admin'),
                email=os.getenv('ADMIN_EMAIL', 'admin@example.com'),
                is_admin=True
            )
            admin.password = os.getenv('ADMIN_PASSWORD', 'admin123')
            db.session.add(admin)
            db.session.commit()
            print("管理员用户已创建")
        else:
            print("管理员用户已存在")
        
        # 创建默认系统配置
        default_configs = {
            # 网站基本信息
            'site_name': '趋于自助商城系统',  # 网站名称，显示在浏览器标签和页面标题
            'site_title': '趋于自助商城系统',  # 网站标题，用于SEO优化
            'site_description': '趋于自助商城系统，人人都可拥有自己的独立商城',  # 网站描述，用于SEO优化
            'site_keywords': '趋于自助商城系统',  # 网站关键词，用于SEO优化
            'about_us': '趋于自助商城系统，人人都可拥有自己的独立商城',  # 关于我们页面内容
            'footer_text': '© 2025 趋于自助商城系统',  # 页脚版权文本
            'footer_link': 'https://github.com/git88848',  # 页脚链接地址

            # 网站资源设置
            'site_url': 'http://127.0.0.1:5000',  # 网站域名，默认为本地开发地址
            'site_logo': '/static/img/logo.png',  # 网站Logo路径，建议尺寸：200x50px
            'site_favicon': '/static/img/favicon.ico',  # 网站图标路径，建议尺寸：32x32px或16x16px

            # 联系方式设置
            'contact_email': 'admin@example.com',  # 联系邮箱
            'contact_phone': '(907) 793-9460',  # 联系电话
            'show_email': '0',  # 是否显示联系邮箱，1显示，0隐藏
            'show_phone': '0',  # 是否显示联系电话，1显示，0隐藏

            # 微信设置
            'site_weixin': 'weixin888',  # 微信号
            'show_weixin': '0',  # 是否显示微信号，1显示，0隐藏

            # Telegram设置
            'telegram_username': 'Lawofforce',  # Telegram用户名
            'telegram_channel': 'QUYUkjpd',  # Telegram频道
            'telegram_group': 'QUYUkjq',  # Telegram群组
            'show_telegram_username': '1',  # 是否显示Telegram用户名，1显示，0隐藏
            'show_telegram_channel': '1',  # 是否显示Telegram频道，1显示，0隐藏
            'show_telegram_group': '1',  # 是否显示Telegram群组，1显示，0隐藏
            'show_telegram_contact': '1',  # 是否显示Telegram联系方式，1显示，0隐藏

            # Telegram机器人设置
            'telegram_bot_token': '7175153476:AAHHtjZ9P_8u0BzQTkeQBJFCY4hLhBSKCRE',  # 机器人Token
            'telegram_chat_id': '-1001923404194',  # 通知发送的目标聊天ID
            'enable_telegram_notify': '1',  # 是否启用Telegram通知，1启用，0禁用

            # 验证码设置
            'enable_captcha': '1',  # 是否启用验证码，1启用，0禁用
        }

        for key, value in default_configs.items():
            config = SystemConfig.query.filter_by(key=key).first()
            if not config:
                config = SystemConfig(key=key, value=value)
                db.session.add(config)
                print(f"系统配置 {key} 已创建")
            else:
                print(f"系统配置 {key} 已存在")
        
        db.session.commit()
        
        # 检查是否已存在易支付配置
        epay_config = EpayConfig.query.filter_by(is_active=True).first()
        if not epay_config:
            # 创建易支付配置
            epay_config = EpayConfig(
                api_url="https://pay.example.com",  # 替换为实际的易支付接口
                pid="1000",
                key="your_key_here",
                notify_url="http://your-domain.com/epay/notify",
                return_url="http://your-domain.com/epay/return",
                is_active=True
            )
            db.session.add(epay_config)
            db.session.commit()
            print("易支付配置已创建")
        else:
            print("易支付配置已存在")

        # 创建默认分类
        default_categories = [
            {
                'name': '游戏充值',
                'description': '各类游戏充值服务',
                'icon': 'bi-controller'
            },
            {
                'name': '账号出售',
                'description': '各类账号商品',
                'icon': 'bi-person-badge'
            },
            {
                'name': '点卡充值',
                'description': '各类点卡充值',
                'icon': 'bi-credit-card'
            },
            {
                'name': '软件服务',
                'description': '各类软件授权与服务',
                'icon': 'bi-pc-display'
            }
        ]

        for cat_data in default_categories:
            category = Category.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = Category(**cat_data)
                db.session.add(category)
                print(f"分类 {cat_data['name']} 已创建")
            else:
                print(f"分类 {cat_data['name']} 已存在")
        
        db.session.commit()

        # 创建默认商品
        default_products = [
            {
                'name': '王者荣耀点券充值',
                'description': '24小时自动充值，充值后请及时查收',
                'price': 98.00,
                'category_name': '游戏充值',
                'stock': 100,
                'sales': 0,
                'status': True,
                'image': 'game-recharge.jpg'
            },
            {
                'name': 'Steam账号',
                'description': '已验证的Steam账号，可以直接使用',
                'price': 15.00,
                'category_name': '账号出售',
                'stock': 50,
                'sales': 0,
                'status': True,
                'image': 'steam-account.jpg'
            },
            {
                'name': '腾讯视频会员',
                'description': '腾讯视频会员月卡，激活后立即生效',
                'price': 25.00,
                'category_name': '点卡充值',
                'stock': 200,
                'sales': 0,
                'status': True,
                'image': 'video-membership.jpg'
            },
            {
                'name': 'Office 365订阅',
                'description': 'Office 365个人版一年订阅，含Word、Excel、PowerPoint等全套软件',
                'price': 199.00,
                'category_name': '软件服务',
                'stock': 80,
                'sales': 0,
                'status': True,
                'image': 'office-subscription.jpg'
            }
        ]

        for prod_data in default_products:
            category_name = prod_data.pop('category_name')
            category = Category.query.filter_by(name=category_name).first()
            if category:
                product = Product.query.filter_by(name=prod_data['name']).first()
                if not product:
                    prod_data['category_id'] = category.id
                    product = Product(**prod_data)
                    db.session.add(product)
                    print(f"商品 {prod_data['name']} 已创建")
                else:
                    print(f"商品 {prod_data['name']} 已存在")
        
        db.session.commit()
        print("数据库初始化完成")

if __name__ == "__main__":
    init_db() 