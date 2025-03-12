import os
import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Category, Product, Card, Order, EpayConfig, SystemConfig, PageView
from app.forms import CategoryForm, ProductForm, CardForm, BatchCardForm, EpayConfigForm, UserEditForm
from . import admin
from sqlalchemy import func, inspect
from app.tasks.order_tasks import handle_expired_orders

def admin_required(f):
    """检查是否为管理员的装饰器"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('您没有权限访问此页面')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin.route('/')
@admin.route('/index')
@login_required
@admin_required
def index():
    """管理后台首页"""
    # 统计数据
    product_count = Product.query.count()
    category_count = Category.query.count()
    order_count = Order.query.count()
    card_count = Card.query.count()
    user_count = User.query.count()
    
    # 最近订单
    recent_orders = Order.query.order_by(Order.create_time.desc()).limit(5).all()
    
    # 最近注册用户
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # 订单状态统计
    order_status_counts = {}
    status_counts = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    for status, count in status_counts:
        order_status_counts[status] = count
    
    # 商品销量排行
    top_products = Product.query.order_by(Product.sales.desc()).limit(5).all()
    
    # 访问统计数据
    import datetime
    today = datetime.datetime.utcnow().date()
    
    # 总访问量
    page_view_count = PageView.query.count()
    
    # 今日访问量
    today_view_count = PageView.query.filter(
        func.date(PageView.created_at) == today
    ).count()
    
    # 昨日访问量
    yesterday = today - datetime.timedelta(days=1)
    yesterday_view_count = PageView.query.filter(
        func.date(PageView.created_at) == yesterday
    ).count()
    
    now = datetime.datetime.now()
    
    return render_template('admin/index.html', 
                          product_count=product_count,
                          category_count=category_count,
                          order_count=order_count,
                          card_count=card_count,
                          user_count=user_count,
                          recent_orders=recent_orders,
                          recent_users=recent_users,
                          order_status_counts=order_status_counts,
                          top_products=top_products,
                          page_view_count=page_view_count,
                          today_view_count=today_view_count,
                          yesterday_view_count=yesterday_view_count,
                          now=now)

# 分类管理
@admin.route('/category')
@login_required
@admin_required
def category_list():
    categories = Category.query.all()
    return render_template('admin/category_list.html', categories=categories)

@admin.route('/category/add', methods=['GET', 'POST'])
@login_required
@admin_required
def category_add():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            icon=form.icon.data
        )
        db.session.add(category)
        db.session.commit()
        flash('分类添加成功')
        return redirect(url_for('admin.category_list'))
    return render_template('admin/category_form.html', form=form)

@admin.route('/category/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def category_edit(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm()
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.icon = form.icon.data
        db.session.commit()
        flash('分类更新成功')
        return redirect(url_for('admin.category_list'))
    
    form.name.data = category.name
    form.description.data = category.description
    form.icon.data = category.icon
    return render_template('admin/category_form.html', form=form, category=category)

@admin.route('/category/delete/<int:id>')
@login_required
@admin_required
def category_delete(id):
    category = Category.query.get_or_404(id)
    
    # 检查是否有关联的商品
    if category.products.count() > 0:
        flash('该分类下有商品，无法删除')
        return redirect(url_for('admin.category_list'))
    
    db.session.delete(category)
    db.session.commit()
    flash('分类删除成功')
    return redirect(url_for('admin.category_list'))

# 商品管理
@admin.route('/product')
@login_required
@admin_required
def product_list():
    products = Product.query.all()
    return render_template('admin/product_list.html', products=products)

@admin.route('/product/add', methods=['GET', 'POST'])
@login_required
@admin_required
def product_add():
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        # 处理图片上传
        image_filename = None
        if form.image.data:
            image = form.image.data
            image_filename = secure_filename(f"{uuid.uuid4().hex}.{image.filename.rsplit('.', 1)[1].lower()}")
            image_path = os.path.join(current_app.root_path, 'static', current_app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)
        
        product = Product(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            image=image_filename,
            stock=form.stock.data,
            status=form.status.data,
            category_id=form.category_id.data
        )
        db.session.add(product)
        db.session.commit()
        flash('商品添加成功')
        return redirect(url_for('admin.product_list'))
    
    return render_template('admin/product_form.html', form=form)

@admin.route('/product/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def product_edit(id):
    product = Product.query.get_or_404(id)
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        # 处理图片上传
        if form.image.data and form.image.data.filename:
            # 删除旧图片
            if product.image:
                old_image_path = os.path.join(current_app.root_path, 'static', current_app.config['UPLOAD_FOLDER'], product.image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # 保存新图片
            image = form.image.data
            image_filename = secure_filename(f"{uuid.uuid4().hex}.{image.filename.rsplit('.', 1)[1].lower()}")
            image_path = os.path.join(current_app.root_path, 'static', current_app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)
            product.image = image_filename
        
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.stock = form.stock.data
        product.status = form.status.data
        product.category_id = form.category_id.data
        
        db.session.commit()
        flash('商品更新成功')
        return redirect(url_for('admin.product_list'))
    
    form.name.data = product.name
    form.description.data = product.description
    form.price.data = product.price
    form.stock.data = product.stock
    form.status.data = product.status
    form.category_id.data = product.category_id
    
    return render_template('admin/product_form.html', form=form, product=product)

@admin.route('/product/delete/<int:id>')
@login_required
@admin_required
def product_delete(id):
    product = Product.query.get_or_404(id)
    
    # 删除商品图片
    if product.image:
        image_path = os.path.join(current_app.root_path, 'static', current_app.config['UPLOAD_FOLDER'], product.image)
        if os.path.exists(image_path):
            os.remove(image_path)
    
    # 删除关联的卡密
    Card.query.filter_by(product_id=product.id).delete()
    
    # 删除商品
    db.session.delete(product)
    db.session.commit()
    flash('商品删除成功')
    return redirect(url_for('admin.product_list'))

# 卡密管理
@admin.route('/card')
@login_required
@admin_required
def card_list():
    product_id = request.args.get('product_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = Card.query
    if product_id:
        query = query.filter_by(product_id=product_id)
    
    pagination = query.order_by(Card.created_at.desc()).paginate(page=page, per_page=20)
    cards = pagination.items
    
    products = Product.query.all()
    return render_template('admin/card_list.html', cards=cards, pagination=pagination, products=products, product_id=product_id)

@admin.route('/card/add', methods=['GET', 'POST'])
@login_required
@admin_required
def card_add():
    form = CardForm()
    form.product_id.choices = [(p.id, p.name) for p in Product.query.all()]
    
    if form.validate_on_submit():
        card = Card(
            card_info=form.card_info.data,
            product_id=form.product_id.data
        )
        db.session.add(card)
        
        # 更新商品库存
        product = Product.query.get(form.product_id.data)
        product.stock += 1
        
        db.session.commit()
        flash('卡密添加成功')
        return redirect(url_for('admin.card_list'))
    
    return render_template('admin/card_form.html', form=form)

@admin.route('/card/batch', methods=['GET', 'POST'])
@login_required
@admin_required
def card_batch():
    form = BatchCardForm()
    form.product_id.choices = [(p.id, p.name) for p in Product.query.all()]
    
    if form.validate_on_submit():
        card_info_list = form.card_info.data.strip().split('\n')
        count = 0
        
        for card_info in card_info_list:
            card_info = card_info.strip()
            if card_info:
                card = Card(
                    card_info=card_info,
                    product_id=form.product_id.data
                )
                db.session.add(card)
                count += 1
        
        # 更新商品库存
        if count > 0:
            product = Product.query.get(form.product_id.data)
            product.stock += count
            db.session.commit()
            flash(f'成功导入 {count} 个卡密')
        else:
            flash('没有导入任何卡密')
        
        return redirect(url_for('admin.card_list'))
    
    return render_template('admin/card_batch.html', form=form)

@admin.route('/card/delete/<int:id>')
@login_required
@admin_required
def card_delete(id):
    card = Card.query.get_or_404(id)
    
    # 如果卡密未售出，减少商品库存
    if card.status == 0:  # 0表示未售出
        product = card.product
        if product.stock > 0:
            product.stock -= 1
    
    db.session.delete(card)
    db.session.commit()
    flash('卡密删除成功')
    return redirect(url_for('admin.card_list'))

# 订单管理
@admin.route('/order')
@login_required
@admin_required
def order_list():
    """订单列表"""
    page = request.args.get('page', 1, type=int)
    query = Order.query
    
    # 筛选条件
    order_id = request.args.get('order_id', '')
    if order_id:
        query = query.filter(Order.order_id.like(f'%{order_id}%'))
    
    status = request.args.get('status', '')
    if status:
        query = query.filter(Order.status == int(status))
    
    # 分页
    pagination = query.order_by(Order.create_time.desc()).paginate(page=page, per_page=20)
    orders = pagination.items
    
    # 传递当前时间用于比较过期时间
    now = datetime.now()
    
    return render_template('admin/order_list.html', orders=orders, pagination=pagination, now=now)

@admin.route('/order/<string:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """订单详情"""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    # 传递当前时间用于比较过期时间
    now = datetime.now()
    return render_template('admin/order_detail.html', order=order, now=now)

@admin.route('/order/cancel/<string:order_id>')
@login_required
@admin_required
def order_cancel(order_id):
    """取消订单"""
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    if order.status != 0:
        flash('只能取消未支付的订单', 'warning')
        return redirect(url_for('admin.order_detail', order_id=order_id))
    
    order.status = -1
    db.session.commit()
    flash('订单已取消', 'success')
    return redirect(url_for('admin.order_detail', order_id=order_id))

@admin.route('/order/batch_delete', methods=['POST'])
@login_required
@admin_required
def order_batch_delete():
    """批量删除订单"""
    order_ids = request.form.getlist('order_ids')
    if not order_ids:
        flash('请选择要删除的订单', 'warning')
        return redirect(url_for('admin.order_list'))
    
    # 查询要删除的订单
    orders = Order.query.filter(Order.order_id.in_(order_ids)).all()
    
    # 删除订单
    count = 0
    for order in orders:
        db.session.delete(order)
        count += 1
    
    db.session.commit()
    flash(f'成功删除 {count} 个订单', 'success')
    return redirect(url_for('admin.order_list'))

@admin.route('/order/delete_all', methods=['POST'])
@login_required
@admin_required
def order_delete_all():
    """一键删除所有订单"""
    # 获取所有订单
    orders = Order.query.all()
    
    # 删除所有订单
    count = 0
    for order in orders:
        db.session.delete(order)
        count += 1
    
    db.session.commit()
    flash(f'成功删除所有订单，共 {count} 个', 'success')
    return redirect(url_for('admin.order_list'))

# 用户管理
@admin.route('/user')
@login_required
@admin_required
def user_list():
    users = User.query.all()
    return render_template('admin/user_list.html', users=users)

@admin.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit(id):
    user = User.query.get_or_404(id)
    form = UserEditForm()
    form.user_id = user.id  # 设置用户ID用于验证
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        if form.password.data:
            user.password = form.password.data
        db.session.add(user)
        db.session.commit()
        flash('用户信息已更新')
        return redirect(url_for('.user_list'))
    
    form.username.data = user.username
    form.email.data = user.email
    return render_template('admin/user_edit.html', form=form, user=user)

@admin.route('/user/delete/<int:id>')
@login_required
@admin_required
def user_delete(id):
    user = User.query.get_or_404(id)
    
    # 删除用户关联的订单
    Order.query.filter_by(user_id=user.id).delete()
    
    # 删除用户关联的卡密
    Card.query.filter_by(user_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    flash('用户删除成功')
    return redirect(url_for('admin.user_list'))

# 易支付配置管理
@admin.route('/epay_config')
@login_required
@admin_required
def epay_config_list():
    """易支付配置列表"""
    try:
        # 打印数据库连接信息
        print(f"数据库URL: {current_app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # 检查表是否存在
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"数据库中的表: {tables}")
        
        if 'epay_config' in tables:
            print("epay_config 表存在")
        else:
            print("epay_config 表不存在")
            # 尝试创建表
            db.create_all()
            print("尝试创建表")
        
        # 查询配置
        configs = EpayConfig.query.all()
        print(f"查询到 {len(configs)} 条配置记录")
        
        return render_template('admin/epay_config_list.html', configs=configs)
    except Exception as e:
        import traceback
        print(f"发生错误: {e}")
        print(traceback.format_exc())
        flash(f'加载易支付配置时出错: {str(e)}', 'danger')
        return render_template('admin/epay_config_list.html', configs=[])

@admin.route('/epay_config/add', methods=['GET', 'POST'])
@login_required
@admin_required
def epay_config_add():
    """添加易支付配置"""
    form = EpayConfigForm()
    
    # 设置默认值
    if request.method == 'GET':
        form.notify_url.data = url_for('main.epay_notify', _external=True)
        form.return_url.data = url_for('main.epay_return', _external=True)
    
    if form.validate_on_submit():
        # 如果设置为启用，则禁用其他配置
        if form.is_active.data:
            EpayConfig.query.update({'is_active': False})
        
        config = EpayConfig(
            api_url=form.api_url.data,
            pid=form.pid.data,
            key=form.key.data,
            notify_url=form.notify_url.data,
            return_url=form.return_url.data,
            is_active=form.is_active.data,
            alipay_enabled=form.alipay_enabled.data,
            wxpay_enabled=form.wxpay_enabled.data,
            qqpay_enabled=form.qqpay_enabled.data
        )
        db.session.add(config)
        db.session.commit()
        
        flash('易支付配置添加成功')
        return redirect(url_for('admin.epay_config_list'))
    
    return render_template('admin/epay_config_form.html', form=form, title='添加易支付配置')

@admin.route('/epay_config/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def epay_config_edit(id):
    """编辑易支付配置"""
    config = EpayConfig.query.get_or_404(id)
    form = EpayConfigForm()
    
    if request.method == 'GET':
        form.api_url.data = config.api_url
        form.pid.data = config.pid
        form.key.data = config.key
        form.notify_url.data = config.notify_url
        form.return_url.data = config.return_url
        form.is_active.data = config.is_active
        form.alipay_enabled.data = config.alipay_enabled if hasattr(config, 'alipay_enabled') else True
        form.wxpay_enabled.data = config.wxpay_enabled if hasattr(config, 'wxpay_enabled') else True
        form.qqpay_enabled.data = config.qqpay_enabled if hasattr(config, 'qqpay_enabled') else True
    
    if form.validate_on_submit():
        # 如果设置为启用，则禁用其他配置
        if form.is_active.data and not config.is_active:
            EpayConfig.query.update({'is_active': False})
        
        config.api_url = form.api_url.data
        config.pid = form.pid.data
        config.key = form.key.data
        config.notify_url = form.notify_url.data
        config.return_url = form.return_url.data
        config.is_active = form.is_active.data
        config.alipay_enabled = form.alipay_enabled.data
        config.wxpay_enabled = form.wxpay_enabled.data
        config.qqpay_enabled = form.qqpay_enabled.data
        config.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('易支付配置更新成功')
        return redirect(url_for('admin.epay_config_list'))
    
    return render_template('admin/epay_config_form.html', form=form, title='编辑易支付配置')

@admin.route('/epay_config/delete/<int:id>')
@login_required
@admin_required
def epay_config_delete(id):
    """删除易支付配置"""
    config = EpayConfig.query.get_or_404(id)
    
    db.session.delete(config)
    db.session.commit()
    
    flash('易支付配置删除成功')
    return redirect(url_for('admin.epay_config_list'))

@admin.route('/system_config', methods=['GET', 'POST'])
@login_required
@admin_required
def system_config():
    """系统设置页面"""
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'site_settings':
            # 处理Logo上传
            if 'site_logo_file' in request.files:
                logo_file = request.files['site_logo_file']
                if logo_file and logo_file.filename:
                    try:
                        # 确保static/img目录存在
                        img_path = os.path.join(current_app.root_path, 'static', 'img')
                        if not os.path.exists(img_path):
                            os.makedirs(img_path)
                        # 保存为logo.png
                        logo_path = os.path.join(img_path, 'logo.png')
                        logo_file.save(logo_path)
                        # 更新配置
                        SystemConfig.set_value('site_logo', '/static/img/logo.png')
                        flash('Logo上传成功', 'success')
                    except Exception as e:
                        flash(f'Logo上传失败：{str(e)}', 'error')
            
            # 处理Favicon上传
            if 'site_favicon_file' in request.files:
                favicon_file = request.files['site_favicon_file']
                if favicon_file and favicon_file.filename:
                    try:
                        # 确保static/img目录存在
                        img_path = os.path.join(current_app.root_path, 'static', 'img')
                        if not os.path.exists(img_path):
                            os.makedirs(img_path)
                        # 保存为favicon.ico
                        favicon_path = os.path.join(img_path, 'favicon.ico')
                        favicon_file.save(favicon_path)
                        # 更新配置
                        SystemConfig.set_value('site_favicon', '/static/img/favicon.ico')
                        flash('网站图标上传成功', 'success')
                    except Exception as e:
                        flash(f'网站图标上传失败：{str(e)}', 'error')
            
            # 获取其他表单数据
            site_name = request.form.get('site_name')
            site_title = request.form.get('site_title')
            site_description = request.form.get('site_description')
            site_keywords = request.form.get('site_keywords')
            about_us = request.form.get('about_us')
            footer_text = request.form.get('footer_text')
            footer_link = request.form.get('footer_link')
            contact_email = request.form.get('contact_email')
            show_email = '1' if request.form.get('show_email') else '0'
            contact_phone = request.form.get('contact_phone')
            show_phone = '1' if request.form.get('show_phone') else '0'
            telegram_username = request.form.get('telegram_username')
            show_telegram_username = '1' if request.form.get('show_telegram_username') else '0'
            telegram_channel = request.form.get('telegram_channel')
            show_telegram_channel = '1' if request.form.get('show_telegram_channel') else '0'
            telegram_group = request.form.get('telegram_group')
            show_telegram_group = '1' if request.form.get('show_telegram_group') else '0'
            site_weixin = request.form.get('site_weixin', '')
            show_weixin = '1' if request.form.get('show_weixin') else '0'
            
            # 验证码设置
            enable_captcha = '1' if request.form.get('enable_captcha') else '0'
            enable_admin_login_captcha = '1' if request.form.get('enable_admin_login_captcha') else '0'
            enable_user_login_captcha = '1' if request.form.get('enable_user_login_captcha') else '0'
            
            # 保存验证码设置
            SystemConfig.set_value('enable_captcha', enable_captcha, '是否启用注册验证码')
            SystemConfig.set_value('enable_admin_login_captcha', enable_admin_login_captcha, '是否启用管理员登录验证码')
            SystemConfig.set_value('enable_user_login_captcha', enable_user_login_captcha, '是否启用用户登录验证码')
            
            # Telegram机器人设置
            telegram_bot_token = request.form.get('telegram_bot_token', '')
            telegram_chat_id = request.form.get('telegram_chat_id', '')
            enable_order_notification = '1' if request.form.get('enable_order_notification') else '0'
            enable_payment_notification = '1' if request.form.get('enable_payment_notification') else '0'
            
            # 保存设置
            SystemConfig.set_value('site_name', site_name or '')
            SystemConfig.set_value('site_title', site_title or '')
            SystemConfig.set_value('site_description', site_description or '')
            SystemConfig.set_value('site_keywords', site_keywords or '')
            SystemConfig.set_value('about_us', about_us or '')
            SystemConfig.set_value('footer_text', footer_text or '')
            SystemConfig.set_value('footer_link', footer_link or '')
            SystemConfig.set_value('contact_email', contact_email or '')
            SystemConfig.set_value('show_email', show_email)
            SystemConfig.set_value('contact_phone', contact_phone or '')
            SystemConfig.set_value('show_phone', show_phone)
            SystemConfig.set_value('telegram_username', telegram_username or '')
            SystemConfig.set_value('show_telegram_username', show_telegram_username)
            SystemConfig.set_value('telegram_channel', telegram_channel or '')
            SystemConfig.set_value('show_telegram_channel', show_telegram_channel)
            SystemConfig.set_value('telegram_group', telegram_group or '')
            SystemConfig.set_value('show_telegram_group', show_telegram_group)
            SystemConfig.set_value('site_weixin', site_weixin or '')
            SystemConfig.set_value('show_weixin', show_weixin)
            
            # 保存网站域名设置
            site_url = request.form.get('site_url', '')
            SystemConfig.set_value('site_url', site_url)
            
            # 保存Telegram机器人设置
            SystemConfig.set_value('telegram_bot_token', telegram_bot_token)
            SystemConfig.set_value('telegram_chat_id', telegram_chat_id)
            SystemConfig.set_value('enable_order_notification', enable_order_notification)
            SystemConfig.set_value('enable_payment_notification', enable_payment_notification)
            
            flash('网站设置已更新', 'success')
            
        elif form_type == 'order_settings':
            # 处理订单设置
            order_expire_minutes = request.form.get('order_expire_minutes', '15')
            order_check_interval = request.form.get('order_check_interval', '60')
            
            # 验证数据
            try:
                expire_minutes = int(order_expire_minutes)
                if expire_minutes <= 0:
                    flash('订单过期时间必须大于0', 'warning')
                    return redirect(url_for('admin.system_config'))
                    
                check_interval = int(order_check_interval)
                if check_interval < 10 or check_interval > 3600:
                    flash('自动检查间隔必须在10-3600秒之间', 'warning')
                    return redirect(url_for('admin.system_config'))
            except ValueError:
                flash('请输入有效的数字', 'warning')
                return redirect(url_for('admin.system_config'))
            
            # 保存订单设置
            SystemConfig.set_value(
                'order_expire_minutes', 
                order_expire_minutes, 
                '订单有效期（分钟），超过该时间未支付的订单将自动取消'
            )
            
            SystemConfig.set_value(
                'order_check_interval', 
                order_check_interval, 
                '系统自动检查过期订单的时间间隔（秒）'
            )
            
            flash('订单设置已更新', 'success')
        
        # 处理微信号设置
        site_weixin = request.form.get('site_weixin', '')
        show_weixin = '1' if request.form.get('show_weixin') else '0'
        
        try:
            # 更新微信号（确保不会传入None值）
            SystemConfig.set_value('site_weixin', site_weixin or '')
            # 更新微信号显示状态
            SystemConfig.set_value('show_weixin', show_weixin)
            
            flash('系统设置已更新', 'success')
        except Exception as e:
            flash(f'更新失败：{str(e)}', 'error')
            
        return redirect(url_for('admin.system_config'))
    
    # GET请求处理
    configs = SystemConfig.query.all()
    config_dict = {item.key: item.value for item in configs}
    
    return render_template('admin/system_config.html',
                         site_name=config_dict.get('site_name', ''),
                         site_description=config_dict.get('site_description', ''),
                         site_keywords=config_dict.get('site_keywords', ''),
                         site_logo=config_dict.get('site_logo', ''),
                         site_favicon=config_dict.get('site_favicon', ''),
                         site_weixin=config_dict.get('site_weixin', ''),
                         show_weixin=config_dict.get('show_weixin') == '1',
                         enable_captcha=config_dict.get('enable_captcha') == '1',
                         enable_admin_login_captcha=config_dict.get('enable_admin_login_captcha') == '1',
                         enable_user_login_captcha=config_dict.get('enable_user_login_captcha') == '1',
                         # 添加订单过期时间和自动检查间隔的配置值
                         order_expire_minutes=config_dict.get('order_expire_minutes', '15'),
                         order_check_interval=config_dict.get('order_check_interval', '60'))

@admin.route('/handle_expired_orders_view')
@login_required
@admin_required
def handle_expired_orders_view():
    """手动处理过期订单视图"""
    result = handle_expired_orders()
    flash(f'处理结果: {result}', 'success')
    return redirect(url_for('admin.order_list'))

# 页面访问统计
@admin.route('/statistics')
@login_required
@admin_required
def statistics():
    """页面访问统计"""
    from sqlalchemy import func
    import datetime
    
    # 获取今天的日期
    today = datetime.datetime.utcnow().date()
    
    # 总访问量
    total_views = PageView.query.count()
    
    # 今日访问量
    today_views = PageView.query.filter(
        func.date(PageView.created_at) == today
    ).count()
    
    # 昨日访问量
    yesterday = today - datetime.timedelta(days=1)
    yesterday_views = PageView.query.filter(
        func.date(PageView.created_at) == yesterday
    ).count()
    
    # 本周访问量
    week_start = today - datetime.timedelta(days=today.weekday())
    week_views = PageView.query.filter(
        func.date(PageView.created_at) >= week_start
    ).count()
    
    # 本月访问量
    month_start = datetime.datetime(today.year, today.month, 1).date()
    month_views = PageView.query.filter(
        func.date(PageView.created_at) >= month_start
    ).count()
    
    # 访问量最多的10个页面
    top_pages = db.session.query(
        PageView.path, 
        func.count(PageView.id).label('count')
    ).group_by(PageView.path).order_by(func.count(PageView.id).desc()).limit(10).all()
    
    # 最近30天的每日访问量
    thirty_days_ago = today - datetime.timedelta(days=30)
    daily_views = db.session.query(
        func.date(PageView.created_at).label('date'),
        func.count(PageView.id).label('count')
    ).filter(
        func.date(PageView.created_at) >= thirty_days_ago
    ).group_by(
        func.date(PageView.created_at)
    ).order_by(
        func.date(PageView.created_at)
    ).all()
    
    # 最近100条访问记录
    recent_views = PageView.query.order_by(PageView.created_at.desc()).limit(100).all()
    
    return render_template(
        'admin/statistics.html',
        total_views=total_views,
        today_views=today_views,
        yesterday_views=yesterday_views,
        week_views=week_views,
        month_views=month_views,
        top_pages=top_pages,
        daily_views=daily_views,
        recent_views=recent_views
    )

@admin.route('/clear_pycache')
@login_required
@admin_required
def clear_pycache():
    """清除所有__pycache__目录"""
    import os
    import shutil
    
    # 获取应用根目录
    root_dir = current_app.root_path
    parent_dir = os.path.dirname(root_dir)
    
    # 计数器
    deleted_count = 0
    
    # 遍历目录查找__pycache__
    for dirpath, dirnames, filenames in os.walk(parent_dir):
        # 检查当前目录中是否有__pycache__
        if '__pycache__' in dirnames:
            pycache_path = os.path.join(dirpath, '__pycache__')
            try:
                # 删除整个__pycache__目录
                shutil.rmtree(pycache_path)
                deleted_count += 1
                current_app.logger.info(f"已删除: {pycache_path}")
            except Exception as e:
                current_app.logger.error(f"删除{pycache_path}时出错: {str(e)}")
    
    flash(f'成功清除了 {deleted_count} 个 __pycache__ 目录', 'success')
    return redirect(url_for('admin.index')) 