from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from sqlalchemy.orm import validates

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    orders = db.relationship('Order', back_populates='user')
    
    @property
    def password(self):
        raise AttributeError('密码不是可读属性')
        
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(64), default='bi-grid-3x3-gap-fill')  # 添加图标字段，默认值为通用图标
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    products = db.relationship('Product', back_populates='category')
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0)
    sales = db.Column(db.Integer, default=0)
    status = db.Column(db.Boolean, default=True)  # True为上架，False为下架
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    image = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    category = db.relationship('Category', back_populates='products')
    orders = db.relationship('Order', back_populates='product')
    cards = db.relationship('Card', back_populates='product')
    
    @validates('image')
    def validate_image(self, key, image):
        if image == '':
            return None
        return image
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Card(db.Model):
    __tablename__ = 'cards'
    
    id = db.Column(db.Integer, primary_key=True)
    card_info = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)  # 0: 未售出, 1: 已售出
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    add_time = db.Column(db.DateTime, default=datetime.now)
    sell_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    product = db.relationship('Product', back_populates='cards')
    order = db.relationship('Order', back_populates='cards')
    
    def __repr__(self):
        return f'<Card {self.id}>'

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(32), unique=True, index=True)  # 订单号
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 允许为空，支持匿名用户
    email = db.Column(db.String(64))  # 匿名用户的邮箱，用于接收卡密
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer, default=1)  # 购买数量
    price = db.Column(db.Float)  # 单价
    total_price = db.Column(db.Float)  # 总价
    status = db.Column(db.Integer, default=0)  # 0: 未支付, 1: 已支付, -1: 已取消
    create_time = db.Column(db.DateTime, default=datetime.now)
    expire_time = db.Column(db.DateTime)  # 订单过期时间
    pay_time = db.Column(db.DateTime)
    pay_type = db.Column(db.String(32))  # 支付方式
    trade_no = db.Column(db.String(64))  # 第三方支付交易号
    
    # 关系
    user = db.relationship('User', back_populates='orders')
    product = db.relationship('Product', back_populates='orders')
    cards = db.relationship('Card', back_populates='order')
    
    def __repr__(self):
        return f'<Order {self.order_id}>'

# 页面访问统计模型
class PageView(db.Model):
    __tablename__ = 'page_views'
    
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255))  # 访问的路径
    ip = db.Column(db.String(64))  # 访问者IP
    user_agent = db.Column(db.String(255))  # 用户代理
    referer = db.Column(db.String(255))  # 来源页面
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 用户ID，未登录为空
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    user = db.relationship('User', backref=db.backref('page_views', lazy='dynamic'))
    
    def __repr__(self):
        return f'<PageView {self.path}>'

class EpayConfig(db.Model):
    """易支付配置模型"""
    __tablename__ = 'epay_config'
    
    id = db.Column(db.Integer, primary_key=True)
    api_url = db.Column(db.String(255), nullable=False, comment='易支付接口地址')
    pid = db.Column(db.String(50), nullable=False, comment='商户ID')
    key = db.Column(db.String(255), nullable=False, comment='商户密钥')
    notify_url = db.Column(db.String(255), nullable=False, comment='异步通知地址')
    return_url = db.Column(db.String(255), nullable=False, comment='同步通知地址')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    alipay_enabled = db.Column(db.Boolean, default=True, comment='是否启用支付宝')
    wxpay_enabled = db.Column(db.Boolean, default=True, comment='是否启用微信支付')
    qqpay_enabled = db.Column(db.Boolean, default=True, comment='是否启用QQ钱包')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<EpayConfig {self.api_url}>'

class SystemConfig(db.Model):
    """系统配置模型"""
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, comment='配置键名')
    value = db.Column(db.Text, nullable=False, comment='配置值')
    description = db.Column(db.String(255), comment='配置描述')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值"""
        config = cls.query.filter_by(key=key).first()
        if config:
            return config.value
        return default
    
    @classmethod
    def set_value(cls, key, value, description=None):
        """设置配置值"""
        config = cls.query.filter_by(key=key).first()
        if config:
            config.value = value
            if description:
                config.description = description
        else:
            config = cls(key=key, value=value, description=description)
            db.session.add(config)
        db.session.commit()
        return config 