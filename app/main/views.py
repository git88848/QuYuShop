import uuid
from datetime import datetime, timedelta
import time
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from app.models import Category, Product, Order, Card, EpayConfig, User, SystemConfig
from app.forms import OrderForm, AnonymousOrderForm
from . import main
from ..utils.epay import Epay
import requests
from app.utils import TelegramNotifier

@main.route('/')
def index():
    """首页"""
    # 获取系统配置
    site_name = SystemConfig.get_value('site_name', '趋于发卡系统')
    site_title = SystemConfig.get_value('site_title', '')
    site_description = SystemConfig.get_value('site_description', '提供各类虚拟商品自动发卡服务，方便快捷，安全可靠。')
    site_keywords = SystemConfig.get_value('site_keywords', '')
    site_logo = SystemConfig.get_value('site_logo', '/static/img/logo.png')
    site_favicon = SystemConfig.get_value('site_favicon', '/static/img/favicon.ico')
    about_us = SystemConfig.get_value('about_us', '')
    footer_text = SystemConfig.get_value('footer_text', '')
    footer_link = SystemConfig.get_value('footer_link', '')
    contact_email = SystemConfig.get_value('contact_email', '')
    contact_phone = SystemConfig.get_value('contact_phone', '')
    site_weixin = SystemConfig.get_value('site_weixin', '')
    telegram_username = SystemConfig.get_value('telegram_username', '')
    telegram_channel = SystemConfig.get_value('telegram_channel', '')
    telegram_group = SystemConfig.get_value('telegram_group', '')
    
    # 获取显示控制配置
    show_email = SystemConfig.get_value('show_email', '0') == '1'
    show_phone = SystemConfig.get_value('show_phone', '0') == '1'
    show_weixin = SystemConfig.get_value('show_weixin', '0') == '1'
    show_telegram_username = SystemConfig.get_value('show_telegram_username', '0') == '1'
    show_telegram_channel = SystemConfig.get_value('show_telegram_channel', '0') == '1'
    show_telegram_group = SystemConfig.get_value('show_telegram_group', '0') == '1'
    
    # 获取分类列表
    categories = Category.query.all()
    
    # 获取商品列表
    products = Product.query.filter_by(status=1).all()
    
    return render_template('main/index.html',
                         site_name=site_name,
                         site_title=site_title,
                         site_description=site_description,
                         site_keywords=site_keywords,
                         site_logo=site_logo,
                         site_favicon=site_favicon,
                         about_us=about_us,
                         footer_text=footer_text,
                         footer_link=footer_link,
                         contact_email=contact_email,
                         contact_phone=contact_phone,
                         site_weixin=site_weixin,
                         telegram_username=telegram_username,
                         telegram_channel=telegram_channel,
                         telegram_group=telegram_group,
                         show_email=show_email,
                         show_phone=show_phone,
                         show_weixin=show_weixin,
                         show_telegram_username=show_telegram_username,
                         show_telegram_channel=show_telegram_channel,
                         show_telegram_group=show_telegram_group,
                         categories=categories,
                         products=products,
                         now=datetime.now())

@main.route('/category/<int:id>')
def category(id):
    category = Category.query.get_or_404(id)
    products = Product.query.filter_by(category_id=id, status=True).all()
    return render_template('main/category.html', category=category, products=products)

@main.route('/products')
def products():
    """所有商品页面"""
    # 获取系统配置
    site_name = SystemConfig.get_value('site_name', '趋于发卡系统')
    
    # 获取所有分类
    categories = Category.query.all()
    
    # 获取所有上架的商品
    products = Product.query.filter_by(status=True).all()
    
    return render_template('main/products.html',
                           site_name=site_name,
                           categories=categories,
                           products=products,
                           config=current_app.config)

@main.route('/product/<int:id>', methods=['GET', 'POST'])
def product(id):
    product = Product.query.get_or_404(id)
    form = OrderForm()
    anon_form = AnonymousOrderForm()
    
    if request.method == 'POST':
        # 确保product_id在表单中
        form.product_id.data = product.id
        anon_form.product_id.data = product.id
        current_app.logger.info(f"收到POST请求：{request.form}")
        
        # 根据提交按钮区分不同的表单
        if 'submit' in request.form:
            if request.form['submit'] == '提交订单':
                # 处理登录用户订单
                if current_user.is_authenticated and form.validate_on_submit():
                    current_app.logger.info("已登录用户表单验证通过")
                    
                    # 检查库存
                    quantity = form.quantity.data
                    if product.stock < quantity:
                        current_app.logger.info(f"库存不足：库存{product.stock}，请求{quantity}")
                        flash('商品库存不足')
                        return redirect(url_for('main.product', id=product.id))
                    
                    # 创建订单
                    order_id = str(uuid.uuid4()).replace('-', '')[:16]
                    current_app.logger.info(f"创建订单：{order_id}")
                    
                    # 获取订单过期时间配置（默认15分钟）
                    expire_minutes = int(SystemConfig.get_value('order_expire_minutes', '15'))
                    expire_time = datetime.now() + timedelta(minutes=expire_minutes)
                    
                    order = Order(
                        order_id=order_id,
                        quantity=quantity,
                        price=product.price,
                        total_price=product.price * quantity,
                        user_id=current_user.id,
                        product_id=product.id,
                        expire_time=expire_time
                    )
                    db.session.add(order)
                    try:
                        db.session.commit()
                        current_app.logger.info(f"订单创建成功：{order.id}")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"订单创建失败：{str(e)}")
                        flash('订单创建失败，请重试')
                        return redirect(url_for('main.product', id=product.id))
                    
                    # 跳转到支付页面
                    current_app.logger.info(f"重定向到支付页面：{url_for('main.pay', order_id=order.order_id)}")
                    return redirect(url_for('main.pay', order_id=order.order_id))
                
            elif request.form['submit'] == '匿名下单':
                # 处理匿名订单
                if anon_form.validate_on_submit():
                    current_app.logger.info("匿名用户表单验证通过")
                    
                    # 检查库存
                    quantity = anon_form.quantity.data
                    if product.stock < quantity:
                        current_app.logger.info(f"库存不足：库存{product.stock}，请求{quantity}")
                        flash('商品库存不足')
                        return redirect(url_for('main.product', id=product.id))
                    
                    # 创建订单
                    order_id = str(uuid.uuid4()).replace('-', '')[:16]
                    current_app.logger.info(f"创建匿名订单：{order_id}")
                    
                    # 获取订单过期时间配置（默认15分钟）
                    expire_minutes = int(SystemConfig.get_value('order_expire_minutes', '15'))
                    expire_time = datetime.now() + timedelta(minutes=expire_minutes)
                    
                    order = Order(
                        order_id=order_id,
                        quantity=quantity,
                        price=product.price,
                        total_price=product.price * quantity,
                        email=anon_form.email.data,
                        product_id=product.id,
                        user_id=None,  # 确保user_id为None
                        expire_time=expire_time
                    )
                    db.session.add(order)
                    try:
                        db.session.commit()
                        current_app.logger.info(f"匿名订单创建成功：{order.id}")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"匿名订单创建失败：{str(e)}")
                        flash('订单创建失败，请重试')
                        return redirect(url_for('main.product', id=product.id))
                    
                    # 跳转到支付页面
                    current_app.logger.info(f"重定向到匿名支付页面：{url_for('main.anonymous_pay', order_id=order.order_id)}")
                    return redirect(url_for('main.anonymous_pay', order_id=order.order_id))
    
    elif request.method == 'POST':
        current_app.logger.error(f"表单验证失败：{form.errors if current_user.is_authenticated else anon_form.errors}")
    
    # 在渲染模板前设置product_id
    form.product_id.data = product.id
    anon_form.product_id.data = product.id
    return render_template('main/product.html', product=product, form=form, anon_form=anon_form)

@main.route('/order')
@login_required
def order_list():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.create_time.desc()).all()
    return render_template('main/order_list.html', orders=orders)

@main.route('/order/<string:order_id>')
@login_required
def order_detail(order_id):
    try:
        order = Order.query.filter_by(order_id=order_id, user_id=current_user.id).first_or_404()
        
        # 如果订单已支付，查询关联的卡密
        cards = []
        if order.status == 1:  # 已支付
            cards = Card.query.filter_by(order_id=order.id).all()
        
        # 传递当前时间用于比较过期时间
        now = datetime.now()
        return render_template('main/order_detail.html', order=order, now=now, cards=cards)
    except Exception as e:
        current_app.logger.error(f"访问订单详情出错: {str(e)}")
        flash('查询订单时出错，请稍后再试', 'danger')
        return redirect(url_for('main.order_list'))

@main.route('/pay_order/<string:order_id>')
def pay_order(order_id):
    """
    模拟支付功能已禁用，用户必须通过易支付完成支付
    """
    # 查询订单
    if current_user.is_authenticated:
        order = Order.query.filter_by(order_id=order_id, user_id=current_user.id).first_or_404()
    else:
        order = Order.query.filter_by(order_id=order_id, user_id=None).first_or_404()
    
    if order.status != 0:
        flash('订单状态不正确', 'warning')
        if current_user.is_authenticated:
            return redirect(url_for('main.order_detail', order_id=order.order_id))
        else:
            return redirect(url_for('main.anonymous_order_detail', order_id=order.order_id, email=order.email))
    
    # 重定向到支付页面
    flash('请选择支付方式完成支付', 'info')
    if current_user.is_authenticated:
        return redirect(url_for('main.pay', order_id=order.order_id))
    else:
        return redirect(url_for('main.anonymous_pay', order_id=order.order_id))

@main.route('/search')
def search():
    keyword = request.args.get('q', '')
    if not keyword:
        return redirect(url_for('main.index'))
    
    products = Product.query.filter(
        Product.name.like(f'%{keyword}%'),
        Product.status == True
    ).all()
    
    return render_template('main/search.html', products=products, keyword=keyword)

# 易支付相关路由
@main.route('/epay/pay/<order_id>', methods=['GET'])
def epay_pay(order_id):
    """
    易支付支付
    """
    # 获取支付方式
    pay_type = request.args.get('type', 'alipay')
    is_ajax = request.args.get('ajax', '0')
    
    # 查询订单
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        if is_ajax == '1':
            return jsonify({'code': -1, 'msg': '订单不存在'})
        flash('订单不存在', 'danger')
        return redirect(url_for('main.index'))
    
    # 检查订单状态
    if order.status == 1:
        if is_ajax == '1':
            return jsonify({'code': -1, 'msg': '订单已支付'})
        flash('订单已支付', 'info')
        if current_user.is_authenticated and order.user_id == current_user.id:
            return redirect(url_for('main.order_detail', order_id=order_id))
        elif not order.user_id:  # 匿名订单
            return redirect(url_for('main.anonymous_order_detail', order_id=order_id, email=order.email))
        else:
            return redirect(url_for('main.index'))
    
    # 获取易支付配置
    config = EpayConfig.query.filter_by(is_active=True).first()
    if not config:
        if is_ajax == '1':
            return jsonify({'code': -1, 'msg': '支付未配置'})
        flash('支付未配置', 'danger')
        if current_user.is_authenticated and order.user_id == current_user.id:
            return redirect(url_for('main.order_detail', order_id=order_id))
        elif not order.user_id:  # 匿名订单
            return redirect(url_for('main.anonymous_order_detail', order_id=order_id, email=order.email))
        else:
            return redirect(url_for('main.index'))
    
    try:
        # 初始化易支付
        epay = Epay(
            api_url=config.api_url,
            pid=config.pid,
            key=config.key
        )
        
        # 构建商品名称
        product_name = f"{order.product.name if order.product else '商品'} x {order.quantity}"
        
        # 使用表单提交方式直接跳转到易支付页面
        current_app.logger.info(f"创建易支付订单：{order_id}，金额：{order.total_price}，支付方式：{pay_type}")
        
        # 生成支付表单
        form_html = epay.submit_order(
            out_trade_no=order_id,
            name=product_name,
            money=str(order.total_price),
            notify_url=config.notify_url,
            return_url=config.return_url,
            pay_type=pay_type
        )
        
        # 返回表单HTML，自动提交
        return form_html
            
    except Exception as e:
        # 处理异常
        current_app.logger.error(f"易支付请求异常: {str(e)}")
        if is_ajax == '1':
            return jsonify({'code': -1, 'msg': f'支付请求异常: {str(e)}'})
        flash(f'支付请求异常: {str(e)}', 'danger')
        if current_user.is_authenticated and order.user_id == current_user.id:
            return redirect(url_for('main.order_detail', order_id=order_id))
        elif not order.user_id:  # 匿名订单
            return redirect(url_for('main.anonymous_order_detail', order_id=order_id, email=order.email))
        else:
            return redirect(url_for('main.index'))

@main.route('/epay/notify', methods=['GET', 'POST'])
def epay_notify():
    """
    易支付异步通知
    """
    # 获取所有参数
    params = request.args.to_dict()
    
    # 记录通知参数，便于调试
    current_app.logger.info(f"易支付异步通知参数: {params}")
    
    # 获取易支付配置
    config = EpayConfig.query.filter_by(is_active=True).first()
    if not config:
        current_app.logger.error("易支付通知：未找到有效配置")
        return 'fail'
    
    # 初始化易支付
    epay = Epay(
        api_url=config.api_url,
        pid=config.pid,
        key=config.key
    )
    
    # 验证通知
    if epay.verify_notify(params):
        # 获取订单号
        out_trade_no = params.get('out_trade_no')
        trade_no = params.get('trade_no')
        
        current_app.logger.info(f"易支付通知验证成功: 订单号={out_trade_no}, 交易号={trade_no}")
        
        # 查询订单
        order = Order.query.filter_by(order_id=out_trade_no).first()
        if order:
            # 更新订单状态
            if order.status == 0:
                order.status = 1  # 已支付
                order.pay_time = datetime.now()
                order.pay_type = '易支付-' + params.get('type', '未知')
                order.trade_no = trade_no
                
                # 分配卡密
                cards = Card.query.filter_by(product_id=order.product_id, status=0).limit(order.quantity).all()
                if len(cards) >= order.quantity:
                    for card in cards:
                        card.status = 1  # 已售出
                        card.order_id = order.id
                        card.sell_time = datetime.now()
                    
                    # 更新商品销量和库存
                    product = order.product
                    product.sales += order.quantity
                    product.stock -= order.quantity
                    
                    try:
                        db.session.commit()
                        current_app.logger.info(f"订单 {out_trade_no} 支付成功，已分配 {len(cards)} 张卡密")
                        
                        # 发送Telegram通知
                        try:
                            TelegramNotifier.send_payment_notification(order)
                        except Exception as e:
                            current_app.logger.error(f"发送Telegram通知失败: {str(e)}")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"更新订单状态失败: {str(e)}")
                        return 'fail'
                else:
                    current_app.logger.error(f"订单 {out_trade_no} 支付成功，但卡密库存不足")
            
            return 'success'  # 返回success表示接收成功
        else:
            current_app.logger.error(f"易支付通知：未找到订单 {out_trade_no}")
    else:
        current_app.logger.error("易支付通知：验证失败")
    
    return 'fail'

@main.route('/epay/return', methods=['GET'])
def epay_return():
    """
    易支付同步通知
    """
    # 获取订单号
    out_trade_no = request.args.get('out_trade_no')
    
    if not out_trade_no:
        flash('无效的订单号', 'warning')
        return redirect(url_for('main.index'))
    
    # 查询订单
    order = Order.query.filter_by(order_id=out_trade_no).first()
    if not order:
        flash('订单不存在', 'warning')
        return redirect(url_for('main.index'))
    
    # 根据是否为匿名订单重定向到不同页面
    if order.user_id is None:
        # 匿名订单
        return redirect(url_for('main.anonymous_order_detail', order_id=out_trade_no, email=order.email))
    else:
        # 登录用户订单
        return redirect(url_for('main.order_detail', order_id=out_trade_no))

# 修改支付页面，添加易支付选项
@main.route('/pay/<string:order_id>', methods=['GET'])
@login_required
def pay(order_id):
    """
    支付页面
    """
    # 查询订单
    order = Order.query.filter_by(order_id=order_id, user_id=current_user.id).first_or_404()
    
    # 检查订单状态
    if order.status == 1:
        flash('该订单已支付', 'info')
        return redirect(url_for('main.order_detail', order_id=order_id))
    
    if order.status != 0:
        flash('该订单状态异常，无法支付', 'warning')
        return redirect(url_for('main.order_detail', order_id=order_id))
    
    # 检查订单是否过期
    now = datetime.now()
    if order.expire_time and order.expire_time < now:
        # 更新订单状态为已过期
        order.status = -2
        db.session.commit()
        flash('该订单已过期，请重新下单', 'warning')
        return redirect(url_for('main.order_detail', order_id=order_id))
    
    # 获取易支付配置
    config = EpayConfig.query.filter_by(is_active=True).first()
    if not config:
        flash('支付未配置', 'danger')
        return redirect(url_for('main.order_detail', order_id=order_id))
    
    # 创建支付配置对象，用于模板中判断支付方式是否可用
    payment_config = {
        'alipay_enabled': hasattr(config, 'alipay_enabled') and config.alipay_enabled,
        'wxpay_enabled': hasattr(config, 'wxpay_enabled') and config.wxpay_enabled,
        'qqpay_enabled': hasattr(config, 'qqpay_enabled') and config.qqpay_enabled
    }
    
    # 如果数据库中没有这些字段，则默认启用所有支付方式
    if not hasattr(config, 'alipay_enabled'):
        payment_config['alipay_enabled'] = True
    if not hasattr(config, 'wxpay_enabled'):
        payment_config['wxpay_enabled'] = True
    if not hasattr(config, 'qqpay_enabled'):
        payment_config['qqpay_enabled'] = True
    
    # 如果后台配置了支付方式，则使用后台配置
    if hasattr(config, 'alipay_enabled'):
        payment_config['alipay_enabled'] = config.alipay_enabled
    if hasattr(config, 'wxpay_enabled'):
        payment_config['wxpay_enabled'] = config.wxpay_enabled
    if hasattr(config, 'qqpay_enabled'):
        payment_config['qqpay_enabled'] = config.qqpay_enabled
    
    return render_template('main/pay.html', order=order, config=payment_config)

# 添加匿名支付页面
@main.route('/anonymous_pay/<string:order_id>', methods=['GET'])
def anonymous_pay(order_id):
    """
    匿名支付页面
    """
    # 查询订单
    order = Order.query.filter_by(order_id=order_id, user_id=None).first_or_404()
    
    # 检查订单状态
    if order.status == 1:
        flash('该订单已支付', 'info')
        return redirect(url_for('main.anonymous_order_detail', order_id=order_id, email=order.email))
    
    # 检查订单是否过期
    if order.expire_time and order.expire_time < datetime.now():
        flash('该订单已过期', 'warning')
        return redirect(url_for('main.anonymous_order_detail', order_id=order_id, email=order.email))
    
    # 获取支付配置
    config = EpayConfig.query.filter_by(is_active=True).first()
    
    # 初始化支付配置
    payment_config = {
        'alipay_enabled': False,
        'wxpay_enabled': False,
        'qqpay_enabled': False
    }
    
    # 如果后台配置了支付方式，则使用后台配置
    if config:
        payment_config['alipay_enabled'] = config.alipay_enabled
        payment_config['wxpay_enabled'] = config.wxpay_enabled
        payment_config['qqpay_enabled'] = config.qqpay_enabled
    
    return render_template('main/anonymous_pay.html', order=order, config=payment_config)

# 添加匿名订单查询功能
@main.route('/anonymous_order')
def anonymous_order_search():
    """
    匿名订单查询页面
    """
    return render_template('main/anonymous_order_search.html')

@main.route('/anonymous_order/query', methods=['POST'])
def anonymous_order_query():
    """
    匿名订单查询
    """
    order_id = request.form.get('order_id')
    email = request.form.get('email')
    
    if not order_id or not email:
        flash('请输入订单号和邮箱', 'warning')
        return redirect(url_for('main.anonymous_order_search'))
    
    order = Order.query.filter_by(order_id=order_id, email=email, user_id=None).first()
    if not order:
        flash('未找到匹配的订单', 'warning')
        return redirect(url_for('main.anonymous_order_search'))
    
    return redirect(url_for('main.anonymous_order_detail', order_id=order_id, email=email))

@main.route('/anonymous_order/<string:order_id>')
def anonymous_order_detail(order_id):
    """
    匿名订单详情页面
    """
    email = request.args.get('email')
    if not email:
        flash('请提供邮箱', 'warning')
        return redirect(url_for('main.anonymous_order_search'))
    
    try:
        # 查询匿名订单
        order = Order.query.filter_by(order_id=order_id, email=email, user_id=None).first_or_404()
        
        # 如果订单已支付，查询关联的卡密
        cards = []
        if order.status == 1:  # 已支付
            cards = Card.query.filter_by(order_id=order.id).all()
            
        # 传递当前时间用于比较过期时间
        now = datetime.now()
        return render_template('main/anonymous_order_detail.html', order=order, now=now, cards=cards)
    except Exception as e:
        current_app.logger.error(f"访问匿名订单详情出错: {str(e)}")
        flash('查询订单时出错，请稍后再试', 'danger')
        return redirect(url_for('main.anonymous_order_search'))

@main.route('/mock_epay', methods=['POST'])
def mock_epay():
    """
    模拟易支付API接口，用于本地测试
    """
    # 获取请求参数
    pid = request.form.get('pid')
    pay_type = request.form.get('type')
    out_trade_no = request.form.get('out_trade_no')
    name = request.form.get('name')
    money = request.form.get('money')
    sign = request.form.get('sign')
    
    # 记录请求
    current_app.logger.info(f"模拟易支付API收到请求：pid={pid}, type={pay_type}, out_trade_no={out_trade_no}, name={name}, money={money}")
    
    # 模拟QR码URL（实际应用中应该根据支付方式生成不同的二维码）
    qr_code_url = url_for('static', filename='img/qrcode_demo.png', _external=True)
    
    # 模拟支付URL
    pay_url = url_for('main.mock_epay_pay', out_trade_no=out_trade_no, _external=True)
    
    # 返回成功响应
    response = {
        'code': 1,
        'msg': '创建订单成功',
        'trade_no': f'MOCK{int(time.time())}',
        'out_trade_no': out_trade_no,
        'type': pay_type,
        'money': money,
        'name': name,
        'qrcode': qr_code_url,
        'payurl': pay_url,
        'status': 0  # 0表示未支付
    }
    
    return jsonify(response)

@main.route('/mock_epay_pay/<out_trade_no>', methods=['GET'])
def mock_epay_pay(out_trade_no):
    """
    模拟易支付支付页面
    """
    # 查询订单
    order = Order.query.filter_by(order_id=out_trade_no).first()
    if not order:
        return render_template('error.html', message='订单不存在')
    
    return render_template('main/mock_epay_pay.html', order=order)

@main.route('/mock_epay_notify', methods=['POST'])
def mock_epay_notify():
    """
    模拟易支付异步通知
    """
    # 获取订单号
    out_trade_no = request.form.get('out_trade_no')
    
    # 查询订单
    order = Order.query.filter_by(order_id=out_trade_no).first()
    if not order:
        return 'fail'
    
    # 更新订单状态
    order.status = 1  # 已支付
    order.paid_at = datetime.now()
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f"模拟易支付异步通知：订单 {out_trade_no} 已支付")
    
    return 'success'

@main.route('/mock_epay_complete/<out_trade_no>', methods=['POST'])
def mock_epay_complete(out_trade_no):
    """
    模拟完成支付
    """
    # 查询订单
    order = Order.query.filter_by(order_id=out_trade_no).first()
    if not order:
        return jsonify({'code': -1, 'msg': '订单不存在'})
    
    # 更新订单状态
    order.status = 1  # 已支付
    order.pay_time = datetime.now()
    order.pay_type = '模拟支付'
    
    # 分配卡密
    cards = Card.query.filter_by(product_id=order.product_id, status=0).limit(order.quantity).all()
    if len(cards) >= order.quantity:
        for card in cards:
            card.status = 1  # 已售出
            card.order_id = order.id
            card.sell_time = datetime.now()
        
        # 更新商品销量和库存
        product = order.product
        product.sales += order.quantity
        product.stock -= order.quantity
        
        db.session.commit()
        
        # 发送Telegram通知
        TelegramNotifier.send_payment_notification(order)
        
        current_app.logger.info(f"模拟完成支付：订单 {out_trade_no} 已支付，已分配 {len(cards)} 张卡密")
        return jsonify({'code': 0, 'msg': '支付成功'})
    else:
        current_app.logger.error(f"模拟完成支付：订单 {out_trade_no} 支付成功，但卡密库存不足")
        return jsonify({'code': -1, 'msg': '支付成功，但卡密库存不足'})

@main.route('/api/send_order_notification/<string:order_id>', methods=['POST'])
def send_order_notification(order_id):
    """
    发送订单通知的API端点
    """
    # 查询订单
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    
    # 发送Telegram通知
    success = TelegramNotifier.send_order_notification(order)
    
    return jsonify({'success': success}) 