import os
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import session
import io
import base64

class CaptchaUtil:
    """验证码工具类"""
    
    @staticmethod
    def generate_code(length=4):
        """生成随机验证码"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    @staticmethod
    def generate_captcha_image(code, width=120, height=40):
        """生成验证码图片"""
        # 创建一个新图像
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            font = ImageFont.truetype('arial.ttf', 30)
        except IOError:
            font = ImageFont.load_default()
        
        # 绘制文本 - 使用新的方法获取文本尺寸
        try:
            # 对于较新版本的Pillow
            left, top, right, bottom = font.getbbox(code)
            text_width = right - left
            text_height = bottom - top
        except AttributeError:
            # 对于较旧版本的Pillow
            try:
                text_width, text_height = draw.textsize(code, font=font)
            except AttributeError:
                # 如果两种方法都不可用，使用估计值
                text_width = len(code) * 15
                text_height = 30
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw.text((x, y), code, font=font, fill=(0, 0, 0))
        
        # 添加干扰线
        for i in range(5):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 255))
        
        # 添加噪点
        for i in range(30):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=(0, 0, 0))
        
        # 将图像转换为字节流
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
    
    @staticmethod
    def generate_captcha_base64(code, width=120, height=40):
        """生成Base64编码的验证码图片"""
        buffer = CaptchaUtil.generate_captcha_image(code, width, height)
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def generate_and_save_captcha():
        """生成验证码并保存到session"""
        code = CaptchaUtil.generate_code()
        session['captcha_code'] = code
        return CaptchaUtil.generate_captcha_image(code)
    
    @staticmethod
    def verify_captcha(session_code, user_input):
        """验证用户输入的验证码"""
        if not session_code or not user_input:
            return False
        return session_code.upper() == user_input.upper() 