from flask import render_template, redirect, request, url_for, flash, session, make_response
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, SystemConfig
from app.forms import LoginForm, RegistrationForm
from . import auth
from app.utils import CaptchaUtil

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # 普通用户登录，检查是否需要验证码
    enable_captcha = SystemConfig.get_value('enable_user_login_captcha', '1') == '1'
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # 验证码验证
        if enable_captcha:
            if not form.captcha.data:
                flash('请输入验证码')
                return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=False)
            if not CaptchaUtil.verify_captcha(session.get('captcha_code', ''), form.captcha.data):
                flash('验证码错误')
                return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=False)
        
        if user is not None and user.verify_password(form.password.data):
            # 检查是否是管理员账号
            if user.is_admin:
                flash('管理员账号请使用管理员登录入口')
                return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=False)
            
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('用户名或密码错误')
        return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=False)
    
    return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=False)

@auth.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.index'))
        return redirect(url_for('main.index'))
    
    # 管理员登录，检查是否需要验证码
    enable_captcha = SystemConfig.get_value('enable_admin_login_captcha', '1') == '1'
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # 验证码验证
        if enable_captcha:
            if not form.captcha.data:
                flash('请输入验证码')
                return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=True)
            if not CaptchaUtil.verify_captcha(session.get('captcha_code', ''), form.captcha.data):
                flash('验证码错误')
                return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=True)
        
        if user is not None and user.verify_password(form.password.data):
            if not user.is_admin:
                flash('您没有管理员权限')
                return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=True)
            
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('admin.index')
            return redirect(next)
        flash('用户名或密码错误')
    
    return render_template('auth/login.html', form=form, enable_captcha=enable_captcha, is_admin=True)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已退出登录')
    return redirect(url_for('main.index'))

@auth.route('/captcha')
def captcha():
    """生成验证码图片"""
    image_io = CaptchaUtil.generate_and_save_captcha()
    response = make_response(image_io.getvalue())
    response.headers['Content-Type'] = 'image/jpeg'
    return response

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # 检查是否启用验证码
    enable_captcha = SystemConfig.get_value('enable_captcha', 'False') == 'True'
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # 验证码验证
        if enable_captcha:
            if not CaptchaUtil.verify_captcha(session.get('captcha_code', ''), form.captcha.data):
                flash('验证码错误，请重新输入', 'danger')
                return render_template('auth/register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form) 