from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, FloatField, IntegerField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange
from app.models import User, Category, Product

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 120), Email()])
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 128)])
    password2 = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码不一致')])
    captcha = StringField('验证码', validators=[DataRequired(), Length(4, 4)])
    submit = SubmitField('注册')
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('用户名已被使用')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('邮箱已被注册')

class CategoryForm(FlaskForm):
    name = StringField('分类名称', validators=[DataRequired(), Length(1, 64)])
    description = TextAreaField('分类描述')
    icon = SelectField('分类图标', choices=[
        ('bi-grid-3x3-gap-fill', '默认图标'),
        ('bi-controller', '游戏手柄'),
        ('bi-person-badge', '用户徽章'),
        ('bi-credit-card', '信用卡'),
        ('bi-cart', '购物车'),
        ('bi-gift', '礼物'),
        ('bi-phone', '手机'),
        ('bi-laptop', '电脑'),
        ('bi-book', '书籍'),
        ('bi-music-note', '音乐'),
        ('bi-film', '视频'),
        ('bi-globe', '全球'),
        ('bi-shield-check', '安全'),
    ])
    submit = SubmitField('提交')

class ProductForm(FlaskForm):
    name = StringField('商品名称', validators=[DataRequired(), Length(1, 128)])
    description = TextAreaField('商品描述')
    price = FloatField('商品价格', validators=[DataRequired()])
    image = FileField('商品图片', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    stock = IntegerField('库存数量', default=0)
    status = BooleanField('上架状态', default=True)
    category_id = SelectField('所属分类', coerce=int, validators=[DataRequired()])
    submit = SubmitField('提交')

class CardForm(FlaskForm):
    product_id = SelectField('所属商品', coerce=int, validators=[DataRequired()])
    card_info = TextAreaField('卡密信息', validators=[DataRequired()])
    submit = SubmitField('提交')

class BatchCardForm(FlaskForm):
    product_id = SelectField('所属商品', coerce=int, validators=[DataRequired()])
    card_info = TextAreaField('卡密信息（每行一个）', validators=[DataRequired()])
    submit = SubmitField('批量导入')

class OrderForm(FlaskForm):
    product_id = HiddenField('商品', validators=[DataRequired()])
    quantity = IntegerField('购买数量', default=1, validators=[DataRequired()])
    submit = SubmitField('提交订单')

class UserEditForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('新密码', validators=[Optional(), Length(6, 128)])
    password2 = PasswordField('确认新密码', validators=[EqualTo('password', message='两次输入的密码不一致')])
    submit = SubmitField('保存')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user and user.id != self.user_id:
            raise ValidationError('用户名已被使用')
    
    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user and user.id != self.user_id:
            raise ValidationError('邮箱已被注册')

class AnonymousOrderForm(FlaskForm):
    product_id = HiddenField('商品', validators=[DataRequired()])
    quantity = IntegerField('购买数量', default=1, validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Length(1, 64), Email()], 
                       description='用于接收卡密信息，请填写正确的邮箱')
    submit = SubmitField('匿名下单')

class EpayConfigForm(FlaskForm):
    api_url = StringField('接口地址', validators=[DataRequired(), Length(1, 255)], 
                         description='易支付接口地址，例如：https://mzf.haohe.de')
    pid = StringField('商户ID', validators=[DataRequired(), Length(1, 50)], 
                     description='易支付商户ID')
    key = StringField('商户密钥', validators=[DataRequired(), Length(1, 255)], 
                     description='易支付商户密钥')
    notify_url = StringField('异步通知地址', validators=[DataRequired(), Length(1, 255)], 
                            description='支付成功后，易支付会向这个地址发送异步通知')
    return_url = StringField('同步通知地址', validators=[DataRequired(), Length(1, 255)], 
                            description='支付成功后，用户浏览器会跳转到这个地址')
    is_active = BooleanField('启用', default=True, 
                            description='是否启用该配置')
    alipay_enabled = BooleanField('启用支付宝', default=True,
                                description='是否启用支付宝支付')
    wxpay_enabled = BooleanField('启用微信支付', default=True,
                               description='是否启用微信支付')
    qqpay_enabled = BooleanField('启用QQ钱包', default=True,
                               description='是否启用QQ钱包支付')
    submit = SubmitField('保存配置') 