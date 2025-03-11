import hashlib
import time
import urllib.parse
import requests
from flask import current_app
from urllib.parse import urlencode, parse_qsl

class Epay:
    """
    易支付接口工具类
    """
    def __init__(self, api_url, pid, key):
        """
        初始化
        :param api_url: 易支付接口地址，例如：https://mzf.haohe.de/
        :param pid: 商户ID
        :param key: 商户密钥
        """
        self.api_url = api_url.rstrip('/')  # 去除末尾的斜杠
        self.pid = pid
        self.key = key
        
    def create_sign(self, params):
        """
        生成签名
        :param params: 参数字典
        :return: 签名字符串
        """
        # 过滤空值和签名参数
        params = {k: v for k, v in params.items() if v and k != 'sign' and k != 'sign_type'}
        
        # 按照参数名ASCII码从小到大排序
        params_sorted = sorted(params.items(), key=lambda x: x[0])
        
        # 拼接成URL键值对的格式
        params_str = '&'.join([f"{k}={v}" for k, v in params_sorted])
        
        # 拼接商户密钥
        sign_str = params_str + self.key
        
        # MD5加密并转为小写
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def submit_order(self, out_trade_no, name, money, notify_url, return_url, pay_type='alipay', param=''):
        """
        创建支付订单（页面跳转支付）
        :param out_trade_no: 商户订单号
        :param name: 商品名称
        :param money: 商品金额
        :param notify_url: 异步通知地址
        :param return_url: 跳转通知地址
        :param pay_type: 支付方式，默认支付宝
        :param param: 业务扩展参数
        :return: 支付表单HTML
        """
        try:
            # 检查参数
            if not out_trade_no or not name or not money:
                current_app.logger.error("易支付创建订单：参数不完整")
                return '<h3>支付参数不完整，请返回重试</h3>'
            
            # 构建参数
            params = {
                'pid': self.pid,
                'type': pay_type,
                'out_trade_no': out_trade_no,
                'notify_url': notify_url,
                'return_url': return_url,
                'name': name,
                'money': money,
                'param': param,
                'sign_type': 'MD5'
            }
            
            # 生成签名
            params['sign'] = self.create_sign(params)
            
            # 记录日志
            current_app.logger.info(f"易支付创建订单：{out_trade_no}，金额：{money}，支付方式：{pay_type}")
            
            # 构建表单
            form_html = f"""
            <form id="epay_submit" name="epay_submit" action="{self.api_url}/submit.php" method="POST">
            """
            for k, v in params.items():
                form_html += f'<input type="hidden" name="{k}" value="{v}" />\n'
            
            form_html += """
            <input type="submit" value="正在跳转到支付页面..." style="display:none;">
            </form>
            <script>document.forms['epay_submit'].submit();</script>
            """
            
            return form_html
        except Exception as e:
            current_app.logger.error(f"易支付创建订单异常：{str(e)}")
            return f'<h3>支付请求发生错误：{str(e)}</h3>'
    
    def api_order(self, out_trade_no, name, money, notify_url, return_url, pay_type='alipay', client_ip='127.0.0.1', device='pc', param=''):
        """
        创建API支付订单
        :param out_trade_no: 商户订单号
        :param name: 商品名称
        :param money: 商品金额
        :param notify_url: 异步通知地址
        :param return_url: 跳转通知地址
        :param pay_type: 支付方式
        :param client_ip: 客户端IP
        :param device: 设备类型
        :param param: 业务扩展参数
        :return: 支付信息字典
        """
        try:
            # 检查参数
            if not out_trade_no or not name or not money:
                current_app.logger.error("易支付API创建订单：参数不完整")
                return {'code': -1, 'msg': '参数不完整'}
            
            # 构建参数
            params = {
                'pid': self.pid,
                'type': pay_type,
                'out_trade_no': out_trade_no,
                'notify_url': notify_url,
                'return_url': return_url,
                'name': name,
                'money': money,
                'clientip': client_ip,
                'device': device,
                'param': param,
                'sign_type': 'MD5'
            }
            
            # 生成签名
            params['sign'] = self.create_sign(params)
            
            # 记录日志
            current_app.logger.info(f"易支付API创建订单：{out_trade_no}，金额：{money}，支付方式：{pay_type}")
            
            # 构建完整的API URL
            api_url = f"{self.api_url}/mapi.php"
            current_app.logger.info(f"请求URL: {api_url}")
            
            # 发送请求
            response = requests.post(api_url, data=params, timeout=10)
            
            # 检查响应状态码
            if response.status_code != 200:
                current_app.logger.error(f"易支付API请求失败：HTTP状态码 {response.status_code}")
                return {'code': -1, 'msg': f'API请求失败：HTTP状态码 {response.status_code}'}
            
            # 解析响应
            try:
                result = response.json()
                current_app.logger.info(f"易支付API响应：{result}")
                return result
            except ValueError:
                current_app.logger.error(f"易支付API响应解析失败：{response.text}")
                return {'code': -1, 'msg': f'API响应解析失败：{response.text[:100]}...'}
        except requests.RequestException as e:
            current_app.logger.error(f"易支付API请求异常：{str(e)}")
            return {'code': -1, 'msg': f'API请求异常：{str(e)}'}
        except Exception as e:
            current_app.logger.error(f"易支付API未知异常：{str(e)}")
            return {'code': -1, 'msg': f'未知异常：{str(e)}'}
    
    def verify_notify(self, params):
        """
        验证异步通知
        :param params: 通知参数
        :return: 验证结果
        """
        try:
            # 记录通知参数
            current_app.logger.info(f"易支付通知参数：{params}")
            
            # 验证支付状态（不同易支付接口可能使用不同的字段）
            trade_status = params.get('trade_status')
            if trade_status is not None and trade_status != 'TRADE_SUCCESS':
                current_app.logger.warning(f"易支付通知：支付状态不是成功，而是 {trade_status}")
                return False
            
            # 有些易支付接口使用status字段
            status = params.get('status')
            if status is not None and status != '1':
                current_app.logger.warning(f"易支付通知：status不是1，而是 {status}")
                return False
            
            # 验证签名
            sign = params.get('sign', '')
            if not sign:
                current_app.logger.warning("易支付通知：签名为空")
                return False
            
            # 计算签名
            calculated_sign = self.create_sign(params)
            
            # 比较签名
            if calculated_sign.lower() != sign.lower():
                current_app.logger.warning(f"易支付通知：签名验证失败，接收到的签名：{sign}，计算的签名：{calculated_sign}")
                return False
            
            current_app.logger.info(f"易支付通知：验证成功，订单号：{params.get('out_trade_no')}")
            return True
        except Exception as e:
            current_app.logger.error(f"易支付通知验证异常：{str(e)}")
            return False
    
    def query_order(self, out_trade_no=None, trade_no=None):
        """
        查询订单
        :param out_trade_no: 商户订单号
        :param trade_no: 系统订单号
        :return: 订单信息
        """
        try:
            # 检查参数
            if not trade_no and not out_trade_no:
                current_app.logger.error("易支付查询订单：订单号不能为空")
                return {'code': -1, 'msg': '订单号不能为空'}
            
            # 构建参数
            params = {
                'act': 'order',
                'pid': self.pid,
                'key': self.key
            }
            
            if trade_no:
                params['trade_no'] = trade_no
            elif out_trade_no:
                params['out_trade_no'] = out_trade_no
            
            # 记录日志
            current_app.logger.info(f"易支付查询订单：{trade_no or out_trade_no}")
            
            # 发送请求
            response = requests.get(f"{self.api_url}/api.php", params=params, timeout=10)
            
            # 检查响应状态码
            if response.status_code != 200:
                current_app.logger.error(f"易支付查询订单失败：HTTP状态码 {response.status_code}")
                return {'code': -1, 'msg': f'查询订单失败：HTTP状态码 {response.status_code}'}
            
            # 解析响应
            try:
                result = response.json()
                current_app.logger.info(f"易支付查询订单响应：{result}")
                return result
            except ValueError:
                current_app.logger.error(f"易支付查询订单响应解析失败：{response.text}")
                return {'code': -1, 'msg': f'响应解析失败：{response.text[:100]}...'}
        except requests.RequestException as e:
            current_app.logger.error(f"易支付查询订单请求异常：{str(e)}")
            return {'code': -1, 'msg': f'查询订单请求异常：{str(e)}'}
        except Exception as e:
            current_app.logger.error(f"易支付查询订单未知异常：{str(e)}")
            return {'code': -1, 'msg': f'未知异常：{str(e)}'}
            
    def query_merchant_info(self):
        """
        查询商户信息
        :return: 商户信息
        """
        try:
            # 构建参数
            params = {
                'act': 'query',
                'pid': self.pid,
                'key': self.key
            }
            
            # 记录日志
            current_app.logger.info(f"易支付查询商户信息：{self.pid}")
            
            # 发送请求
            response = requests.get(f"{self.api_url}/api.php", params=params, timeout=10)
            
            # 检查响应状态码
            if response.status_code != 200:
                current_app.logger.error(f"易支付查询商户信息失败：HTTP状态码 {response.status_code}")
                return {'code': -1, 'msg': f'查询商户信息失败：HTTP状态码 {response.status_code}'}
            
            # 解析响应
            try:
                result = response.json()
                current_app.logger.info(f"易支付查询商户信息响应：{result}")
                return result
            except ValueError:
                current_app.logger.error(f"易支付查询商户信息响应解析失败：{response.text}")
                return {'code': -1, 'msg': f'响应解析失败：{response.text[:100]}...'}
        except requests.RequestException as e:
            current_app.logger.error(f"易支付查询商户信息请求异常：{str(e)}")
            return {'code': -1, 'msg': f'查询商户信息请求异常：{str(e)}'}
        except Exception as e:
            current_app.logger.error(f"易支付查询商户信息未知异常：{str(e)}")
            return {'code': -1, 'msg': f'未知异常：{str(e)}'}

    def sign(self, params):
        """
        签名
        :param params: 参数
        :return: 签名
        """
        # 移除空值参数
        params = {k: v for k, v in params.items() if v != ''}
        
        # 按照键名排序
        params = dict(sorted(params.items()))
        
        # 拼接字符串
        query = urlencode(params)
        query += f"&key={self.key}"
        
        # MD5签名
        return hashlib.md5(query.encode()).hexdigest() 