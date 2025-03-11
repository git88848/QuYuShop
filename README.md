# 趋于自助商城系统 (QuYu Shop) 部署指南

## 一、系统介绍
趋于自助商城系统是一款功能完善的自助发卡平台，支持多种支付方式，提供用户友好的界面和强大的后台管理功能。系统采用现代化设计，响应式布局，完美适配手机、平板和电脑等各种设备。

## 二、部署步骤
### 1. 宝塔面板基础配置
1. **创建网站**
   - 进入宝塔面板 → 网站 → 添加站点
   - 填写域名、选择PHP版本（不需要选择）
   - 创建数据库并记住数据库名、用户名和密码

2. **上传代码**
   - 进入网站目录：`/www/wwwroot/你的站点目录`
   - 上传项目压缩包 `QuYuShop.zip` 并解压

3. **修改配置文件**
   编辑 `.env` 文件填入成你自己的信息

### 2. 配置Python环境
> 注意：CentOS已预装 `Python3.6.8` 和 `pip 9.0.3` 环境
1. **检查Python版本**
   ```bash
   python3 --version
   ```

2. **检查pip3版本**
   ```bash
   pip3 --version
   ```
   
### 3. 创建虚拟环境
1. **进入站点目录**
   ```bash
   cd /www/wwwroot/你的站点目录
   ```
   
3. **创建虚拟环境**
   ```bash
   python3 -m venv 环境名称
   例如：
   python3 -m venv myenv
   ```
   
4. **激活虚拟环境（Linux/Mac）**
   ```bash
   source myenv/bin/activate
   ```
   
5. **安装项目依赖**
   ```bash
   pip3 install -r requirements.txt
   ```
   
### 4. 初始化与启动
1. **初始化数据库**
   ```bash
   python3 init_db.py
   # 当提示确认时，输入y并回车
   ```

2. **启动应用**
   ```bash
   # 后台运行应用
   nohup python3 run.py > web.log 2>&1 &
   
   # 查看进程
   ps aux | grep "python3 run.py"
   ```

### 5. 配置站点
1. **设置反向代理**
   - 进入宝塔面板 → 网站 → 设置 → 反向代理
   - 添加反向代理：
     - 代理名称：QuYuShop
     - 目标URL：`http://你的服务器IP:5000`

2. **配置防火墙**
   - 进入宝塔面板 → 安全 → 防火墙
   - 放行5000端口：
     - 端口：5000
     - 协议：TCP
     - 备注：Flask应用

## 三、访问系统
- **前台访问**：`http://你的域名`
- **后台访问**：`http://你的域名/admin`
- **默认管理员账号**：在`.env`文件中设置的ADMIN_USERNAME和ADMIN_PASSWORD

## 四、常见问题
1. **无法访问网站**
   - 检查Flask应用是否正在运行：`ps aux | grep "python3 run.py"`
   - 检查防火墙是否放行5000端口
   - 检查反向代理配置是否正确
   - 查看日志文件：`tail -f web.log`

2. **上传图片失败**
   - 确保上传目录是否有权限：
   ```bash
   chmod -R 755 /www/wwwroot/你的站点目录/app/static/uploads
   # 这个命令设置目录权限为755，表示：
   # 7 (所有者): 读(4)+写(2)+执行(1)权限
   # 5 (用户组): 读(4)+执行(1)权限
   # 5 (其他用户): 读(4)+执行(1)权限
   # -R 表示递归设置，即目录及其所有子目录和文件都应用此权限
   ```

3. **重启应用**
   ```bash
   进入你的网站目录
   cd /www/wwwroot/你的站点目录

   # 激活虚拟环境（Linux/Mac）
   source myenv/bin/activate

   # 找到进程ID
   ps aux | grep "python3 run.py"

   # 终止进程
   kill <进程ID>
   
   # 重新启动
   nohup python3 run.py > web.log 2>&1 &
   ```
