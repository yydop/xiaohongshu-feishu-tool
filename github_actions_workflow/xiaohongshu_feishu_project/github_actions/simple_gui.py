import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import threading
import configparser
import requests
from bs4 import BeautifulSoup
import re
import time
import random
import datetime
import base64
import hashlib
import urllib.parse

# 简化版本 - 小红书笔记提取并上传飞书多维表格工具
# 专为Windows环境优化，减少依赖项

class SimpleLogger:
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
        
    def info(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - INFO - {message}"
        print(log_message)
        if self.text_widget:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, log_message + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
    
    def error(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - ERROR - {message}"
        print(log_message)
        if self.text_widget:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, log_message + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)

# 小红书笔记模型
class Note:
    def __init__(self):
        self.note_id = ""
        self.title = ""
        self.desc = ""
        self.user_id = ""
        self.nickname = ""
        self.avatar = ""
        self.ip_location = ""
        self.liked_count = 0
        self.collected_count = 0
        self.comment_count = 0
        self.share_count = 0
        self.note_type = "normal"
        self.image_list = []
        self.tag_list = []
        self.upload_time = ""
        
    def to_dict(self):
        return {
            "note_id": self.note_id,
            "title": self.title,
            "desc": self.desc,
            "user_id": self.user_id,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "ip_location": self.ip_location,
            "liked_count": self.liked_count,
            "collected_count": self.collected_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "note_type": self.note_type,
            "image_list": self.image_list,
            "tag_list": self.tag_list,
            "upload_time": self.upload_time
        }

# 用户模型
class User:
    def __init__(self):
        self.user_id = ""
        self.nickname = ""
        self.avatar = ""
        self.desc = ""
        self.gender = 0
        self.follows = 0
        self.fans = 0
        self.notes_count = 0
        self.location = ""
        
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "desc": self.desc,
            "gender": self.gender,
            "follows": self.follows,
            "fans": self.fans,
            "notes_count": self.notes_count,
            "location": self.location
        }

# 小红书提取器
class SimpleXHSExtractor:
    def __init__(self, cookie, output_dir="data/images", logger=None):
        self.cookie = cookie
        self.output_dir = output_dir
        self.logger = logger or SimpleLogger()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        self.headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.xiaohongshu.com",
            "Referer": "https://www.xiaohongshu.com/"
        }
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_note_id(self, url_or_id):
        """从URL或ID中提取笔记ID"""
        if not url_or_id:
            return None
            
        # 如果是完整URL，提取ID部分
        if url_or_id.startswith("http"):
            match = re.search(r"/explore/(\w+)", url_or_id)
            if match:
                return match.group(1)
        
        # 如果已经是ID，直接返回
        if re.match(r"^\w+$", url_or_id):
            return url_or_id
            
        return None
    
    def extract_user_id(self, url_or_id):
        """从URL或ID中提取用户ID"""
        if not url_or_id:
            return None
            
        # 如果是完整URL，提取ID部分
        if url_or_id.startswith("http"):
            match = re.search(r"/user/profile/(\w+)", url_or_id)
            if match:
                return match.group(1)
        
        # 如果已经是ID，直接返回
        if re.match(r"^\w+$", url_or_id):
            return url_or_id
            
        return None
    
    def extract_note(self, url_or_id):
        """提取单个笔记信息"""
        note_id = self.extract_note_id(url_or_id)
        if not note_id:
            self.logger.error(f"无效的笔记URL或ID: {url_or_id}")
            return None
        
        self.logger.info(f"开始提取笔记: {note_id}")
        
        try:
            # 构建API URL
            api_url = f"https://www.xiaohongshu.com/explore/{note_id}"
            
            # 发送请求
            response = requests.get(api_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"提取笔记失败: {response.status_code} {response.reason}")
                return None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取JSON数据
            script_tags = soup.find_all('script')
            note_data = None
            
            for script in script_tags:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    json_str = script.string.split('window.__INITIAL_STATE__=')[1].split(';')[0]
                    data = json.loads(json_str)
                    if 'note' in data and 'noteData' in data['note']:
                        note_data = data['note']['noteData']
                        break
            
            if not note_data:
                self.logger.error(f"未找到笔记数据: {note_id}")
                return None
            
            # 创建笔记对象
            note = Note()
            note.note_id = note_id
            note.title = note_data.get('title', '')
            note.desc = note_data.get('desc', '')
            note.user_id = note_data.get('userId', '')
            note.nickname = note_data.get('nickname', '')
            note.avatar = note_data.get('avatar', '')
            note.ip_location = note_data.get('ipLocation', '')
            note.liked_count = note_data.get('likedCount', 0)
            note.collected_count = note_data.get('collectedCount', 0)
            note.comment_count = note_data.get('commentCount', 0)
            note.share_count = note_data.get('shareCount', 0)
            
            # 提取图片列表
            if 'imageList' in note_data:
                for img in note_data['imageList']:
                    if 'url' in img:
                        note.image_list.append(img['url'])
            
            # 提取标签列表
            if 'tagList' in note_data:
                for tag in note_data['tagList']:
                    if 'name' in tag:
                        note.tag_list.append(tag['name'])
            
            # 提取发布时间
            if 'time' in note_data:
                note.upload_time = note_data['time']
            
            self.logger.info(f"成功提取笔记: {note.title}")
            
            # 下载图片
            if note.image_list:
                self.download_images(note)
            
            return note
            
        except Exception as e:
            self.logger.error(f"提取笔记出错: {str(e)}")
            return None
    
    def extract_user(self, url_or_id):
        """提取用户信息"""
        user_id = self.extract_user_id(url_or_id)
        if not user_id:
            self.logger.error(f"无效的用户URL或ID: {url_or_id}")
            return None
        
        self.logger.info(f"开始提取用户信息: {user_id}")
        
        try:
            # 构建API URL
            api_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            
            # 发送请求
            response = requests.get(api_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"提取用户信息失败: {response.status_code} {response.reason}")
                return None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取JSON数据
            script_tags = soup.find_all('script')
            user_data = None
            
            for script in script_tags:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    json_str = script.string.split('window.__INITIAL_STATE__=')[1].split(';')[0]
                    data = json.loads(json_str)
                    if 'user' in data and 'userPageData' in data['user']:
                        user_data = data['user']['userPageData']
                        break
            
            if not user_data:
                self.logger.error(f"未找到用户数据: {user_id}")
                return None
            
            # 创建用户对象
            user = User()
            user.user_id = user_id
            user.nickname = user_data.get('nickname', '')
            user.avatar = user_data.get('images', '')
            user.desc = user_data.get('desc', '')
            user.gender = user_data.get('gender', 0)
            user.follows = user_data.get('follows', 0)
            user.fans = user_data.get('fans', 0)
            user.notes_count = user_data.get('notes', 0)
            user.location = user_data.get('location', '')
            
            self.logger.info(f"成功提取用户信息: {user.nickname}")
            return user
            
        except Exception as e:
            self.logger.error(f"提取用户信息出错: {str(e)}")
            return None
    
    def search_notes(self, keyword, sort_type=0, limit=20):
        """搜索笔记"""
        self.logger.info(f"搜索笔记: {keyword}")
        
        try:
            # 构建API URL
            api_url = f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}&sort={sort_type}&page=1"
            
            # 发送请求
            response = requests.get(api_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"搜索笔记失败: {response.status_code} {response.reason}")
                return []
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取JSON数据
            script_tags = soup.find_all('script')
            search_data = None
            
            for script in script_tags:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    json_str = script.string.split('window.__INITIAL_STATE__=')[1].split(';')[0]
                    data = json.loads(json_str)
                    if 'search' in data and 'items' in data['search']:
                        search_data = data['search']['items']
                        break
            
            if not search_data:
                self.logger.error(f"未找到搜索结果: {keyword}")
                return []
            
            # 提取笔记ID
            note_ids = []
            for item in search_data:
                if 'id' in item and len(note_ids) < limit:
                    note_ids.append(item['id'])
            
            self.logger.info(f"搜索结果: 找到 {len(note_ids)} 个笔记")
            return note_ids
            
        except Exception as e:
            self.logger.error(f"搜索笔记出错: {str(e)}")
            return []
    
    def extract_user_notes(self, user_id, limit=20):
        """提取用户的笔记"""
        user_id = self.extract_user_id(user_id)
        if not user_id:
            self.logger.error(f"无效的用户ID: {user_id}")
            return []
        
        self.logger.info(f"提取用户笔记: {user_id}")
        
        try:
            # 构建API URL
            api_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            
            # 发送请求
            response = requests.get(api_url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"提取用户笔记失败: {response.status_code} {response.reason}")
                return []
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取JSON数据
            script_tags = soup.find_all('script')
            notes_data = None
            
            for script in script_tags:
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    json_str = script.string.split('window.__INITIAL_STATE__=')[1].split(';')[0]
                    data = json.loads(json_str)
                    if 'user' in data and 'notes' in data['user']:
                        notes_data = data['user']['notes']
                        break
            
            if not notes_data:
                self.logger.error(f"未找到用户笔记: {user_id}")
                return []
            
            # 提取笔记ID
            note_ids = []
            for note in notes_data:
                if 'id' in note and len(note_ids) < limit:
                    note_ids.append(note['id'])
            
            # 提取笔记详情
            notes = []
            for note_id in note_ids:
                note = self.extract_note(note_id)
                if note:
                    notes.append(note)
                    time.sleep(random.uniform(1, 2))  # 随机延迟，避免请求过快
            
            self.logger.info(f"成功提取 {len(notes)} 个用户笔记")
            return notes
            
        except Exception as e:
            self.logger.error(f"提取用户笔记出错: {str(e)}")
            return []
    
    def download_images(self, note):
        """下载笔记中的图片"""
        if not note or not note.image_list:
            return
        
        # 创建笔记目录
        note_dir = os.path.join(self.output_dir, f"{note.nickname}_{note.user_id}", f"{note.title}_{note.note_id}")
        os.makedirs(note_dir, exist_ok=True)
        
        for i, img_url in enumerate(note.image_list):
            try:
                self.logger.info(f"开始下载图片: {img_url}")
                
                # 发送请求
                response = requests.get(img_url, headers={"User-Agent": self.user_agent}, timeout=30)
                
                if response.status_code != 200:
                    self.logger.error(f"下载图片失败: {response.status_code} {response.reason}")
                    continue
                
                # 保存图片
                img_path = os.path.join(note_dir, f"image_{i}.jpg")
                with open(img_path, "wb") as f:
                    f.write(response.content)
                
                self.logger.info(f"成功下载图片: {img_path}")
                
            except Exception as e:
                self.logger.error(f"下载图片出错: {str(e)}")
                continue
            
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(0.5, 1.5))

# 飞书认证
class SimpleFeishuAuth:
    def __init__(self, app_id, app_secret, logger=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.logger = logger or SimpleLogger()
        self.token = None
        self.token_expire_time = 0
        
    def get_tenant_access_token(self):
        """获取tenant_access_token"""
        # 如果token未过期，直接返回
        current_time = int(time.time())
        if self.token and current_time < self.token_expire_time - 300:  # 提前5分钟刷新
            return self.token
        
        self.logger.info("获取新的tenant_access_token")
        
        try:
            # 构建请求
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            data = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"获取tenant_access_token失败: {response.status_code} {response.reason}")
                return None
            
            # 解析响应
            result = response.json()
            if result.get("code") != 0:
                self.logger.error(f"获取tenant_access_token失败: {result.get('msg')}")
                return None
            
            # 保存token
            self.token = result.get("tenant_access_token")
            self.token_expire_time = current_time + result.get("expire", 7200)
            
            self.logger.info(f"成功获取tenant_access_token，有效期: {result.get('expire')}秒")
            return self.token
            
        except Exception as e:
            self.logger.error(f"获取tenant_access_token出错: {str(e)}")
            return None

# 飞书多维表格
class SimpleFeishuBitable:
    def __init__(self, auth, logger=None):
        self.auth = auth
        self.logger = logger or SimpleLogger()
        
    def create_app(self, name):
        """创建多维表格应用"""
        self.logger.info(f"创建多维表格应用: {name}")
        
        try:
            # 获取token
            token = self.auth.get_tenant_access_token()
            if not token:
                return None
            
            # 构建请求
            url = "https://open.feishu.cn/open-apis/bitable/v1/apps"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}"
            }
            data = {
                "name": name
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"创建多维表格应用失败: {response.status_code} {response.reason}")
                return None
            
            # 解析响应
            result = response.json()
            if result.get("code") != 0:
                self.logger.error(f"创建多维表格应用失败: {result.get('msg')}")
                return None
            
            # 获取app_token
            app_token = result.get("data", {}).get("app", {}).get("app_token")
            
            self.logger.info(f"成功创建多维表格应用，app_token: {app_token}")
            return app_token
            
        except Exception as e:
            self.logger.error(f"创建多维表格应用出错: {str(e)}")
            return None
    
    def create_table(self, app_token, name):
        """创建数据表"""
        self.logger.info(f"创建数据表: {name}")
        
        try:
            # 获取token
            token = self.auth.get_tenant_access_token()
            if not token:
                return None
            
            # 构建请求
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}"
            }
            data = {
                "table": {
                    "name": name
                }
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"创建数据表失败: {response.status_code} {response.reason}")
                return None
            
            # 解析响应
            result = response.json()
            if result.get("code") != 0:
                self.logger.error(f"创建数据表失败: {result.get('msg')}")
                return None
            
            # 获取table_id
            table_id = result.get("data", {}).get("table", {}).get("table_id")
            
            self.logger.info(f"成功创建数据表，table_id: {table_id}")
            return table_id
            
        except Exception as e:
            self.logger.error(f"创建数据表出错: {str(e)}")
            return None
    
    def create_field(self, app_token, table_id, field_name, field_type):
        """创建字段"""
        self.logger.info(f"创建字段: {field_name} ({field_type})")
        
        try:
            # 获取token
            token = self.auth.get_tenant_access_token()
            if not token:
                return None
            
            # 构建请求
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}"
            }
            
            # 根据字段类型设置不同的字段属性
            field_data = {
                "field_name": field_name
            }
            
            if field_type == "文本":
                field_data["type"] = "text"
            elif field_type == "数字":
                field_data["type"] = "number"
            elif field_type == "多行文本":
                field_data["type"] = "text"
                field_data["property"] = {"multiple": True}
            elif field_type == "日期时间":
                field_data["type"] = "datetime"
            elif field_type == "附件":
                field_data["type"] = "attachment"
            else:
                field_data["type"] = "text"
            
            data = {
                "field": field_data
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"创建字段失败: {response.status_code} {response.reason}")
                return None
            
            # 解析响应
            result = response.json()
            if result.get("code") != 0:
                self.logger.error(f"创建字段失败: {result.get('msg')}")
                return None
            
            # 获取field_id
            field_id = result.get("data", {}).get("field", {}).get("field_id")
            
            self.logger.info(f"成功创建字段，field_id: {field_id}")
            return field_id
            
        except Exception as e:
            self.logger.error(f"创建字段出错: {str(e)}")
            return None
    
    def list_fields(self, app_token, table_id):
        """获取字段列表"""
        self.logger.info(f"获取字段列表")
        
        try:
            # 获取token
            token = self.auth.get_tenant_access_token()
            if not token:
                return None
            
            # 构建请求
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 发送请求
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.logger.error(f"获取字段列表失败: {response.status_code} {response.reason}")
                return None
            
            # 解析响应
            result = response.json()
            if result.get("code") != 0:
                self.logger.error(f"获取字段列表失败: {result.get('msg')}")
                return None
            
            # 获取字段列表
            fields = result.get("data", {}).get("items", [])
            
            self.logger.info(f"成功获取字段列表，共 {len(fields)} 个字段")
            return fields
            
        except Exception as e:
            self.logger.error(f"获取字段列表出错: {str(e)}")
            return None
    
    def setup_xiaohongshu_table(self, app_token):
        """设置小红书笔记表格"""
        self.logger.info("设置小红书笔记表格")
        
        try:
            # 创建数据表
            table_id = self.create_table(app_token, "小红书笔记")
            if not table_id:
                return None
            
            # 创建字段
            fields = [
                ("笔记ID", "文本"),
                ("标题", "文本"),
                ("内容", "多行文本"),
                ("用户ID", "文本"),
                ("用户名", "文本"),
                ("IP归属地", "文本"),
                ("笔记类型", "文本"),
                ("笔记链接", "文本"),
                ("点赞数", "数字"),
                ("收藏数", "数字"),
                ("评论数", "数字"),
                ("分享数", "数字"),
                ("粉丝数", "数字"),
                ("发布时间", "日期时间"),
                ("标签", "多行文本"),
                ("图片", "附件")
            ]
            
            field_map = {}
            for field_name, field_type in fields:
                field_id = self.create_field(app_token, table_id, field_name, field_type)
                if field_id:
                    field_map[field_name] = field_id
            
            self.logger.info(f"成功设置小红书笔记表格，创建了 {len(field_map)} 个字段")
            return {
                "table_id": table_id,
                "field_map": field_map
            }
            
        except Exception as e:
            self.logger.error(f"设置小红书笔记表格出错: {str(e)}")
            return None
    
    def upload_image(self, app_token, table_id, field_id, image_path):
        """上传图片"""
        self.logger.info(f"上传图片: {image_path}")
        
        try:
            # 获取token
            token = self.auth.get_tenant_access_token()
            if not token:
                return None
            
            # 检查文件是否存在
            if not os.path.exists(image_path):
                self.logger.error(f"图片文件不存在: {image_path}")
                return None
            
            # 构建请求
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}/attachments"
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            # 读取文件
            with open(image_path, "rb") as f:
                files = {
                    "file": (os.path.basename(image_path), f, "image/jpeg")
                }
                
                # 发送请求
                response = requests.post(url, headers=headers, files=files, timeout=60)
            
            if response.status_code != 200:
                self.logger.error(f"上传图片失败: {response.status_code} {response.reason}")
                return None
            
            # 解析响应
            result = response.json()
            if result.get("code") != 0:
                self.logger.error(f"上传图片失败: {result.get('msg')}")
                return None
            
            # 获取file_token
            file_token = result.get("data", {}).get("file_token")
            
            self.logger.info(f"成功上传图片，file_token: {file_token}")
            return file_token
            
        except Exception as e:
            self.logger.error(f"上传图片出错: {str(e)}")
            return None
    
    def convert_xiaohongshu_note_to_record(self, note, user, field_map, image_paths=None):
        """将小红书笔记转换为飞书记录"""
        try:
            record = {}
            
            # 添加笔记信息
            if "笔记ID" in field_map and hasattr(note, "note_id"):
                record[field_map["笔记ID"]] = note.note_id
            
            if "标题" in field_map and hasattr(note, "title"):
                record[field_map["标题"]] = note.title
            
            if "内容" in field_map and hasattr(note, "desc"):
                record[field_map["内容"]] = note.desc
            
            if "用户ID" in field_map and hasattr(note, "user_id"):
                record[field_map["用户ID"]] = note.user_id
            
            if "用户名" in field_map and hasattr(note, "nickname"):
                record[field_map["用户名"]] = note.nickname
            
            if "IP归属地" in field_map and hasattr(note, "ip_location"):
                record[field_map["IP归属地"]] = note.ip_location
            
            if "笔记类型" in field_map and hasattr(note, "note_type"):
                record[field_map["笔记类型"]] = note.note_type
            
            if "笔记链接" in field_map and hasattr(note, "note_id"):
                record[field_map["笔记链接"]] = f"https://www.xiaohongshu.com/explore/{note.note_id}"
            
            if "点赞数" in field_map and hasattr(note, "liked_count"):
                record[field_map["点赞数"]] = note.liked_count
            
            if "收藏数" in field_map and hasattr(note, "collected_count"):
                record[field_map["收藏数"]] = note.collected_count
            
            if "评论数" in field_map and hasattr(note, "comment_count"):
                record[field_map["评论数"]] = note.comment_count
            
            if "分享数" in field_map and hasattr(note, "share_count"):
                record[field_map["分享数"]] = note.share_count
            
            if "发布时间" in field_map and hasattr(note, "upload_time") and note.upload_time:
                # 转换时间格式
                if isinstance(note.upload_time, int):
                    # 毫秒时间戳转ISO格式
                    dt = datetime.datetime.fromtimestamp(note.upload_time / 1000)
                    record[field_map["发布时间"]] = dt.isoformat()
                else:
                    record[field_map["发布时间"]] = note.upload_time
            
            if "标签" in field_map and hasattr(note, "tag_list") and note.tag_list:
                record[field_map["标签"]] = ", ".join(note.tag_list)
            
            # 添加用户信息
            if user:
                if "粉丝数" in field_map and hasattr(user, "fans"):
                    record[field_map["粉丝数"]] = user.fans
            
            # 添加图片路径（用于后续上传）
            if "图片" in field_map and image_paths:
                record["_image_paths"] = image_paths
            
            return record
            
        except Exception as e:
            self.logger.error(f"转换笔记记录出错: {str(e)}")
            return None
    
    def batch_create_records(self, app_token, table_id, records):
        """批量创建记录"""
        self.logger.info(f"批量创建记录: {len(records)}条")
        
        try:
            # 获取token
            token = self.auth.get_tenant_access_token()
            if not token:
                return None
            
            # 构建请求
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {token}"
            }
            
            # 分批处理，每次最多10条
            batch_size = 10
            record_ids = []
            
            for i in range(0, len(records), batch_size):
                batch_records = records[i:i+batch_size]
                
                data = {
                    "records": [{"fields": record} for record in batch_records]
                }
                
                # 发送请求
                response = requests.post(url, headers=headers, json=data, timeout=60)
                
                if response.status_code != 200:
                    self.logger.error(f"批量创建记录失败: {response.status_code} {response.reason}")
                    continue
                
                # 解析响应
                result = response.json()
                if result.get("code") != 0:
                    self.logger.error(f"批量创建记录失败: {result.get('msg')}")
                    continue
                
                # 获取record_ids
                batch_record_ids = [record.get("record_id") for record in result.get("data", {}).get("records", [])]
                record_ids.extend(batch_record_ids)
                
                self.logger.info(f"成功创建 {len(batch_record_ids)} 条记录")
                
                # 避免请求过快
                time.sleep(1)
            
            self.logger.info(f"批量创建记录完成，共 {len(record_ids)} 条")
            return record_ids
            
        except Exception as e:
            self.logger.error(f"批量创建记录出错: {str(e)}")
            return None

# GUI界面
class SimpleXiaohongshuFeishuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("小红书笔记提取并上传飞书多维表格工具")
        self.root.geometry("800x600")
        
        # 创建变量
        self.xhs_cookie = tk.StringVar()
        self.feishu_app_id = tk.StringVar()
        self.feishu_app_secret = tk.StringVar()
        self.output_dir = tk.StringVar(value="data/images")
        self.config_name = tk.StringVar()
        self.extract_mode = tk.StringVar(value="url")
        self.note_url = tk.StringVar()
        self.keyword = tk.StringVar()
        self.user_id = tk.StringVar()
        self.count = tk.IntVar(value=10)
        self.sort_type = tk.IntVar(value=0)
        self.download_images = tk.BooleanVar(value=True)
        self.upload_to_feishu = tk.BooleanVar(value=False)
        self.create_table = tk.BooleanVar(value=True)
        self.app_token = tk.StringVar()
        self.table_id = tk.StringVar()
        self.save_to_file = tk.BooleanVar(value=True)
        self.output_file = tk.StringVar(value="results.json")
        
        # 创建配置目录
        os.makedirs("gui_configs", exist_ok=True)
        
        # 加载配置列表
        self.config_list = self.load_config_list()
        
        # 创建主框架
        self.create_widgets()
        
        # 初始化提取器和结果
        self.extractor = None
        self.notes = []
        self.users = {}
        self.running = False
        
    def create_widgets(self):
        # 创建选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建各个选项卡
        self.create_config_tab()
        self.create_extract_tab()
        self.create_feishu_tab()
        self.create_result_tab()
        self.create_log_tab()
        
    def create_config_tab(self):
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="配置管理")
        
        # 配置选择框架
        select_frame = ttk.LabelFrame(config_frame, text="配置选择")
        select_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(select_frame, text="配置名称:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.config_combo = ttk.Combobox(select_frame, textvariable=self.config_name, values=self.config_list)
        self.config_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        btn_frame = ttk.Frame(select_frame)
        btn_frame.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="加载", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="删除", command=self.delete_config).pack(side=tk.LEFT, padx=5)
        
        # 小红书配置框架
        xhs_frame = ttk.LabelFrame(config_frame, text="小红书配置")
        xhs_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(xhs_frame, text="Cookie:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(xhs_frame, textvariable=self.xhs_cookie, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(xhs_frame, text="从文件加载", command=self.load_cookie_from_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(xhs_frame, text="输出目录:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(xhs_frame, textvariable=self.output_dir, width=50).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(xhs_frame, text="选择目录", command=self.select_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
        # 飞书配置框架
        feishu_frame = ttk.LabelFrame(config_frame, text="飞书配置")
        feishu_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(feishu_frame, text="App ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(feishu_frame, textvariable=self.feishu_app_id, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(feishu_frame, text="App Secret:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(feishu_frame, textvariable=self.feishu_app_secret, width=50, show="*").grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 测试按钮
        test_frame = ttk.Frame(config_frame)
        test_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(test_frame, text="测试小红书配置", command=self.test_xhs_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(test_frame, text="测试飞书配置", command=self.test_feishu_config).pack(side=tk.LEFT, padx=5)
        
    def create_extract_tab(self):
        extract_frame = ttk.Frame(self.notebook)
        self.notebook.add(extract_frame, text="数据提取")
        
        # 提取模式选择
        mode_frame = ttk.LabelFrame(extract_frame, text="提取模式")
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Radiobutton(mode_frame, text="单个笔记URL", variable=self.extract_mode, value="url").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="关键词搜索", variable=self.extract_mode, value="keyword").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="用户笔记", variable=self.extract_mode, value="user").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="批量URL", variable=self.extract_mode, value="batch").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 提取参数框架
        param_frame = ttk.LabelFrame(extract_frame, text="提取参数")
        param_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # URL输入
        self.url_frame = ttk.Frame(param_frame)
        ttk.Label(self.url_frame, text="笔记URL:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(self.url_frame, textvariable=self.note_url, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 关键词输入
        self.keyword_frame = ttk.Frame(param_frame)
        ttk.Label(self.keyword_frame, text="关键词:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(self.keyword_frame, textvariable=self.keyword, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(self.keyword_frame, text="排序方式:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        sort_frame = ttk.Frame(self.keyword_frame)
        sort_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(sort_frame, text="综合排序", variable=self.sort_type, value=0).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sort_frame, text="最热", variable=self.sort_type, value=1).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(sort_frame, text="最新", variable=self.sort_type, value=2).pack(side=tk.LEFT, padx=5)
        
        # 用户ID输入
        self.user_frame = ttk.Frame(param_frame)
        ttk.Label(self.user_frame, text="用户ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(self.user_frame, textvariable=self.user_id, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 批量URL输入
        self.batch_frame = ttk.Frame(param_frame)
        ttk.Label(self.batch_frame, text="URL列表文件:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.batch_file_var = tk.StringVar()
        ttk.Entry(self.batch_frame, textvariable=self.batch_file_var, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Button(self.batch_frame, text="选择文件", command=self.select_batch_file).grid(row=0, column=2, padx=5, pady=5)
        
        # 通用参数
        common_frame = ttk.Frame(param_frame)
        ttk.Label(common_frame, text="提取数量:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Spinbox(common_frame, from_=1, to=100, textvariable=self.count, width=10).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Checkbutton(common_frame, text="下载图片", variable=self.download_images).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # 输出选项
        output_frame = ttk.LabelFrame(extract_frame, text="输出选项")
        output_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(output_frame, text="保存到文件", variable=self.save_to_file).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Label(output_frame, text="输出文件:").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(output_frame, textvariable=self.output_file, width=30).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Button(output_frame, text="选择文件", command=self.select_output_file).grid(row=0, column=3, padx=5, pady=5)
        
        # 执行按钮
        btn_frame = ttk.Frame(extract_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="开始提取", command=self.start_extraction)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止提取", command=self.stop_extraction, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        progress_frame = ttk.Frame(extract_frame)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, length=500, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 初始显示URL输入框
        self.url_frame.pack(fill=tk.X, padx=5, pady=5)
        common_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 绑定提取模式变更事件
        self.extract_mode.trace("w", self.update_extract_mode)
        
    def create_feishu_tab(self):
        feishu_frame = ttk.Frame(self.notebook)
        self.notebook.add(feishu_frame, text="飞书上传")
        
        # 上传选项
        upload_frame = ttk.LabelFrame(feishu_frame, text="上传选项")
        upload_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(upload_frame, text="上传到飞书多维表格", variable=self.upload_to_feishu).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        
        # 表格选项
        table_frame = ttk.LabelFrame(feishu_frame, text="表格选项")
        table_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Radiobutton(table_frame, text="创建新表格", variable=self.create_table, value=True).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(table_frame, text="使用现有表格", variable=self.create_table, value=False).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(table_frame, text="应用Token:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(table_frame, textvariable=self.app_token, width=50).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(table_frame, text="表格ID:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(table_frame, textvariable=self.table_id, width=50).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
    def create_result_tab(self):
        result_frame = ttk.Frame(self.notebook)
        self.notebook.add(result_frame, text="结果查看")
        
        # 笔记列表
        list_frame = ttk.LabelFrame(result_frame, text="笔记列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.note_tree = ttk.Treeview(list_frame, columns=("title", "user", "likes", "comments"), show="headings", height=10)
        self.note_tree.heading("title", text="标题")
        self.note_tree.heading("user", text="用户")
        self.note_tree.heading("likes", text="点赞数")
        self.note_tree.heading("comments", text="评论数")
        self.note_tree.column("title", width=300)
        self.note_tree.column("user", width=150)
        self.note_tree.column("likes", width=100)
        self.note_tree.column("comments", width=100)
        self.note_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定选择事件
        self.note_tree.bind("<<TreeviewSelect>>", self.on_note_select)
        
        # 笔记详情
        detail_frame = ttk.LabelFrame(result_frame, text="笔记详情")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建详情文本框
        self.detail_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, height=10)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_log_tab(self):
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="日志")
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建日志处理器
        self.logger = SimpleLogger(self.log_text)
        
    def update_extract_mode(self, *args):
        # 隐藏所有参数框架
        self.url_frame.pack_forget()
        self.keyword_frame.pack_forget()
        self.user_frame.pack_forget()
        self.batch_frame.pack_forget()
        
        # 根据选择的模式显示对应的参数框架
        mode = self.extract_mode.get()
        if mode == "url":
            self.url_frame.pack(fill=tk.X, padx=5, pady=5)
        elif mode == "keyword":
            self.keyword_frame.pack(fill=tk.X, padx=5, pady=5)
        elif mode == "user":
            self.user_frame.pack(fill=tk.X, padx=5, pady=5)
        elif mode == "batch":
            self.batch_frame.pack(fill=tk.X, padx=5, pady=5)
    
    def load_config_list(self):
        """加载配置列表"""
        config_files = [f.replace(".json", "") for f in os.listdir("gui_configs") if f.endswith(".json")]
        return config_files
    
    def load_config(self):
        """加载选中的配置"""
        config_name = self.config_name.get()
        if not config_name:
            messagebox.showwarning("警告", "请选择配置名称")
            return
        
        config_file = os.path.join("gui_configs", f"{config_name}.json")
        if not os.path.exists(config_file):
            messagebox.showwarning("警告", f"配置文件 {config_file} 不存在")
            return
        
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # 加载配置到界面
            self.xhs_cookie.set(config.get("xhs_cookie", ""))
            self.feishu_app_id.set(config.get("feishu_app_id", ""))
            self.feishu_app_secret.set(config.get("feishu_app_secret", ""))
            self.output_dir.set(config.get("output_dir", "data/images"))
            self.extract_mode.set(config.get("extract_mode", "url"))
            self.note_url.set(config.get("note_url", ""))
            self.keyword.set(config.get("keyword", ""))
            self.user_id.set(config.get("user_id", ""))
            self.count.set(config.get("count", 10))
            self.sort_type.set(config.get("sort_type", 0))
            self.download_images.set(config.get("download_images", True))
            self.upload_to_feishu.set(config.get("upload_to_feishu", False))
            self.create_table.set(config.get("create_table", True))
            self.app_token.set(config.get("app_token", ""))
            self.table_id.set(config.get("table_id", ""))
            self.save_to_file.set(config.get("save_to_file", True))
            self.output_file.set(config.get("output_file", "results.json"))
            
            if "batch_file" in config:
                self.batch_file_var.set(config["batch_file"])
            
            messagebox.showinfo("成功", f"成功加载配置: {config_name}")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存当前配置"""
        config_name = self.config_name.get()
        if not config_name:
            messagebox.showwarning("警告", "请输入配置名称")
            return
        
        config = {
            "xhs_cookie": self.xhs_cookie.get(),
            "feishu_app_id": self.feishu_app_id.get(),
            "feishu_app_secret": self.feishu_app_secret.get(),
            "output_dir": self.output_dir.get(),
            "extract_mode": self.extract_mode.get(),
            "note_url": self.note_url.get(),
            "keyword": self.keyword.get(),
            "user_id": self.user_id.get(),
            "count": self.count.get(),
            "sort_type": self.sort_type.get(),
            "download_images": self.download_images.get(),
            "upload_to_feishu": self.upload_to_feishu.get(),
            "create_table": self.create_table.get(),
            "app_token": self.app_token.get(),
            "table_id": self.table_id.get(),
            "save_to_file": self.save_to_file.get(),
            "output_file": self.output_file.get(),
            "batch_file": self.batch_file_var.get()
        }
        
        config_file = os.path.join("gui_configs", f"{config_name}.json")
        
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 更新配置列表
            if config_name not in self.config_list:
                self.config_list.append(config_name)
                self.config_combo["values"] = self.config_list
            
            messagebox.showinfo("成功", f"成功保存配置: {config_name}")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def delete_config(self):
        """删除选中的配置"""
        config_name = self.config_name.get()
        if not config_name:
            messagebox.showwarning("警告", "请选择配置名称")
            return
        
        config_file = os.path.join("gui_configs", f"{config_name}.json")
        if not os.path.exists(config_file):
            messagebox.showwarning("警告", f"配置文件 {config_file} 不存在")
            return
        
        if messagebox.askyesno("确认", f"确定要删除配置 {config_name} 吗？"):
            try:
                os.remove(config_file)
                
                # 更新配置列表
                self.config_list.remove(config_name)
                self.config_combo["values"] = self.config_list
                self.config_name.set("")
                
                messagebox.showinfo("成功", f"成功删除配置: {config_name}")
                
            except Exception as e:
                messagebox.showerror("错误", f"删除配置失败: {str(e)}")
    
    def load_cookie_from_file(self):
        """从文件加载Cookie"""
        file_path = filedialog.askopenfilename(title="选择Cookie文件", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    cookie = f.read().strip()
                self.xhs_cookie.set(cookie)
                messagebox.showinfo("成功", "成功加载Cookie")
            except Exception as e:
                messagebox.showerror("错误", f"加载Cookie失败: {str(e)}")
    
    def select_output_dir(self):
        """选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir.set(dir_path)
    
    def select_batch_file(self):
        """选择批量URL文件"""
        file_path = filedialog.askopenfilename(title="选择URL列表文件", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            self.batch_file_var.set(file_path)
    
    def select_output_file(self):
        """选择输出文件"""
        file_path = filedialog.asksaveasfilename(title="选择输出文件", defaultextension=".json", filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")])
        if file_path:
            self.output_file.set(file_path)
    
    def test_xhs_config(self):
        """测试小红书配置"""
        cookie = self.xhs_cookie.get()
        if not cookie:
            messagebox.showwarning("警告", "请输入小红书Cookie")
            return
        
        try:
            # 初始化提取器
            extractor = SimpleXHSExtractor(
                cookie=cookie,
                output_dir=self.output_dir.get(),
                logger=self.logger
            )
            
            # 测试搜索功能
            self.logger.info("测试小红书配置...")
            note_ids = extractor.search_notes("测试", sort_type=0, limit=1)
            
            if note_ids:
                messagebox.showinfo("成功", "小红书配置测试成功")
            else:
                messagebox.showwarning("警告", "小红书配置测试失败，未能获取搜索结果")
                
        except Exception as e:
            messagebox.showerror("错误", f"小红书配置测试失败: {str(e)}")
    
    def test_feishu_config(self):
        """测试飞书配置"""
        app_id = self.feishu_app_id.get()
        app_secret = self.feishu_app_secret.get()
        
        if not app_id or not app_secret:
            messagebox.showwarning("警告", "请输入飞书App ID和App Secret")
            return
        
        try:
            # 初始化认证
            auth = SimpleFeishuAuth(app_id, app_secret, logger=self.logger)
            
            # 测试获取token
            self.logger.info("测试飞书配置...")
            token = auth.get_tenant_access_token()
            
            if token:
                messagebox.showinfo("成功", "飞书配置测试成功")
            else:
                messagebox.showwarning("警告", "飞书配置测试失败，未能获取token")
                
        except Exception as e:
            messagebox.showerror("错误", f"飞书配置测试失败: {str(e)}")
    
    def start_extraction(self):
        """开始提取数据"""
        # 检查配置
        cookie = self.xhs_cookie.get()
        if not cookie:
            messagebox.showwarning("警告", "请输入小红书Cookie")
            return
        
        # 检查提取模式
        mode = self.extract_mode.get()
        if mode == "url" and not self.note_url.get():
            messagebox.showwarning("警告", "请输入笔记URL")
            return
        elif mode == "keyword" and not self.keyword.get():
            messagebox.showwarning("警告", "请输入关键词")
            return
        elif mode == "user" and not self.user_id.get():
            messagebox.showwarning("警告", "请输入用户ID")
            return
        elif mode == "batch" and not self.batch_file_var.get():
            messagebox.showwarning("警告", "请选择URL列表文件")
            return
        
        # 检查飞书配置
        if self.upload_to_feishu.get():
            if not self.feishu_app_id.get() or not self.feishu_app_secret.get():
                messagebox.showwarning("警告", "请输入飞书App ID和App Secret")
                return
            
            if not self.create_table.get() and (not self.app_token.get() or not self.table_id.get()):
                messagebox.showwarning("警告", "请输入应用Token和表格ID")
                return
        
        # 更新UI状态
        self.start_btn["state"] = tk.DISABLED
        self.stop_btn["state"] = tk.NORMAL
        self.running = True
        self.progress_bar["value"] = 0
        
        # 清空结果
        self.notes = []
        self.users = {}
        self.note_tree.delete(*self.note_tree.get_children())
        self.detail_text.delete(1.0, tk.END)
        
        # 启动提取线程
        self.extract_thread = threading.Thread(target=self.run_extraction)
        self.extract_thread.daemon = True
        self.extract_thread.start()
    
    def run_extraction(self):
        """运行提取过程"""
        try:
            # 初始化提取器
            self.extractor = SimpleXHSExtractor(
                cookie=self.xhs_cookie.get(),
                output_dir=self.output_dir.get(),
                logger=self.logger
            )
            
            # 根据模式提取数据
            mode = self.extract_mode.get()
            count = self.count.get()
            
            if mode == "url":
                # 提取单个笔记
                url = self.note_url.get()
                self.logger.info(f"提取单个笔记: {url}")
                note = self.extractor.extract_note(url)
                if note:
                    self.logger.info(f"成功提取笔记: {note.title}")
                    self.notes.append(note)
                    
                    # 提取用户信息
                    if note.user_id:
                        user = self.extractor.extract_user(note.user_id)
                        if user:
                            self.users[note.user_id] = user
                else:
                    self.logger.error("笔记提取失败")
                
            elif mode == "keyword":
                # 搜索并提取笔记
                keyword = self.keyword.get()
                sort_type = self.sort_type.get()
                self.logger.info(f"搜索笔记: {keyword}")
                note_ids = self.extractor.search_notes(keyword, sort_type=sort_type)
                
                # 限制数量
                if count and count < len(note_ids):
                    note_ids = note_ids[:count]
                
                self.logger.info(f"开始提取 {len(note_ids)} 个笔记")
                for i, note_id in enumerate(note_ids):
                    if not self.running:
                        break
                    
                    self.logger.info(f"提取第 {i+1}/{len(note_ids)} 个笔记: {note_id}")
                    note = self.extractor.extract_note(note_id)
                    if note:
                        self.logger.info(f"成功提取笔记: {note.title}")
                        self.notes.append(note)
                        
                        # 提取用户信息
                        if note.user_id and note.user_id not in self.users:
                            user = self.extractor.extract_user(note.user_id)
                            if user:
                                self.users[note.user_id] = user
                    else:
                        self.logger.error(f"笔记 {note_id} 提取失败")
                    
                    # 更新进度
                    self.root.after(0, lambda i=i, total=len(note_ids): self.update_progress(i+1, total))
                
            elif mode == "user":
                # 提取用户的所有笔记
                user_id = self.user_id.get()
                self.logger.info(f"提取用户笔记: {user_id}")
                
                # 提取用户信息
                user = self.extractor.extract_user(user_id)
                if user:
                    self.users[user.user_id] = user
                    
                    # 提取用户笔记
                    user_notes = self.extractor.extract_user_notes(user_id, count)
                    self.notes.extend(user_notes)
                    self.logger.info(f"成功提取 {len(user_notes)} 个笔记")
                else:
                    self.logger.error(f"用户 {user_id} 提取失败")
                
            elif mode == "batch":
                # 从文件加载URL列表
                batch_file = self.batch_file_var.get()
                if not os.path.exists(batch_file):
                    self.logger.error(f"URL列表文件不存在: {batch_file}")
                    return
                
                with open(batch_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                # 限制数量
                if count and count < len(urls):
                    urls = urls[:count]
                
                self.logger.info(f"从文件加载了 {len(urls)} 个URL")
                for i, url in enumerate(urls):
                    if not self.running:
                        break
                    
                    self.logger.info(f"提取第 {i+1}/{len(urls)} 个笔记: {url}")
                    note = self.extractor.extract_note(url)
                    if note:
                        self.logger.info(f"成功提取笔记: {note.title}")
                        self.notes.append(note)
                        
                        # 提取用户信息
                        if note.user_id and note.user_id not in self.users:
                            user = self.extractor.extract_user(note.user_id)
                            if user:
                                self.users[note.user_id] = user
                    else:
                        self.logger.error(f"笔记 {url} 提取失败")
                    
                    # 更新进度
                    self.root.after(0, lambda i=i, total=len(urls): self.update_progress(i+1, total))
            
            # 保存结果到文件
            if self.save_to_file.get() and self.notes:
                output_file = self.output_file.get()
                self.logger.info(f"保存结果到文件: {output_file}")
                
                # 转换为可序列化的格式
                result = {
                    "notes": [note.to_dict() for note in self.notes],
                    "users": {user_id: user.to_dict() for user_id, user in self.users.items()}
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"成功保存结果到文件: {output_file}")
            
            # 上传到飞书多维表格
            if self.upload_to_feishu.get() and self.notes:
                self.upload_to_feishu_bitable()
            
            # 更新结果显示
            self.root.after(0, self.update_result_display)
            
            self.logger.info(f"成功提取 {len(self.notes)} 个笔记，{len(self.users)} 个用户信息")
            self.logger.info("提取完成")
            
        except Exception as e:
            self.logger.error(f"提取过程出错: {str(e)}")
        finally:
            # 恢复UI状态
            self.root.after(0, self.reset_ui)
    
    def upload_to_feishu_bitable(self):
        """上传数据到飞书多维表格"""
        self.logger.info("开始上传数据到飞书多维表格")
        
        try:
            # 初始化飞书认证
            app_id = self.feishu_app_id.get()
            app_secret = self.feishu_app_secret.get()
            
            auth = SimpleFeishuAuth(app_id, app_secret, logger=self.logger)
            bitable = SimpleFeishuBitable(auth, logger=self.logger)
            
            # 获取或创建多维表格应用
            app_token = self.app_token.get()
            if not app_token or self.create_table.get():
                table_name = "小红书笔记"
                self.logger.info(f"创建新的多维表格应用: {table_name}")
                app_token = bitable.create_app(table_name)
                if not app_token:
                    self.logger.error("创建多维表格应用失败")
                    return
                self.logger.info(f"成功创建多维表格应用，app_token: {app_token}")
                self.app_token.set(app_token)
            else:
                self.logger.info(f"使用现有的多维表格应用，app_token: {app_token}")
            
            # 获取或创建数据表
            table_id = self.table_id.get()
            field_map = None
            
            if not table_id or self.create_table.get():
                self.logger.info("创建新的数据表")
                table_info = bitable.setup_xiaohongshu_table(app_token)
                if not table_info:
                    self.logger.error("创建数据表失败")
                    return
                
                table_id = table_info["table_id"]
                field_map = table_info["field_map"]
                self.logger.info(f"成功创建数据表，table_id: {table_id}")
                self.table_id.set(table_id)
            else:
                self.logger.info(f"使用现有的数据表，table_id: {table_id}")
                # 获取字段列表
                fields = bitable.list_fields(app_token, table_id)
                if not fields:
                    self.logger.error("获取字段列表失败")
                    return
                
                # 构建字段映射
                field_map = {}
                for field in fields:
                    field_name = field.get("field_name")
                    field_id = field.get("field_id")
                    if field_name and field_id:
                        field_map[field_name] = field_id
            
            # 上传数据
            records = []
            for note in self.notes:
                # 获取对应的用户信息
                user = None
                if note.user_id in self.users:
                    user = self.users[note.user_id]
                
                # 获取图片路径
                image_paths = []
                if hasattr(note, "image_list") and note.image_list and self.download_images.get():
                    note_dir = os.path.join(self.output_dir.get(), f"{note.nickname}_{note.user_id}", f"{note.title}_{note.note_id}")
                    for i in range(len(note.image_list)):
                        img_path = os.path.join(note_dir, f"image_{i}.jpg")
                        if os.path.exists(img_path):
                            image_paths.append(img_path)
                
                # 转换为记录
                record = bitable.convert_xiaohongshu_note_to_record(note, user, field_map, image_paths)
                if record:
                    records.append(record)
            
            if not records:
                self.logger.warning("没有可上传的记录")
                return
            
            self.logger.info(f"准备上传 {len(records)} 条记录")
            
            # 上传图片
            for record in records:
                if "_image_paths" in record and "图片" in field_map:
                    image_tokens = []
                    for image_path in record["_image_paths"]:
                        if os.path.exists(image_path):
                            file_token = bitable.upload_image(app_token, table_id, field_map["图片"], image_path)
                            if file_token:
                                image_tokens.append({"file_token": file_token})
                    
                    if image_tokens:
                        record[field_map["图片"]] = image_tokens
                    
                    # 删除临时字段
                    del record["_image_paths"]
            
            # 批量创建记录
            record_ids = bitable.batch_create_records(app_token, table_id, records)
            
            if record_ids:
                self.logger.info(f"成功上传 {len(record_ids)} 条记录")
                return True
            else:
                self.logger.error("上传记录失败")
                return False
            
        except Exception as e:
            self.logger.error(f"上传到飞书多维表格出错: {str(e)}")
            return False
    
    def update_progress(self, current, total):
        """更新进度条"""
        progress = int(current / total * 100)
        self.progress_bar["value"] = progress
    
    def reset_ui(self):
        """重置UI状态"""
        self.start_btn["state"] = tk.NORMAL
        self.stop_btn["state"] = tk.DISABLED
        self.running = False
        self.progress_bar["value"] = 100
    
    def stop_extraction(self):
        """停止提取"""
        self.running = False
        self.logger.info("正在停止提取...")
    
    def update_result_display(self):
        """更新结果显示"""
        # 清空树形视图
        self.note_tree.delete(*self.note_tree.get_children())
        
        # 添加笔记到树形视图
        for note in self.notes:
            user_name = note.nickname if hasattr(note, "nickname") else ""
            likes = note.liked_count if hasattr(note, "liked_count") else 0
            comments = note.comment_count if hasattr(note, "comment_count") else 0
            
            self.note_tree.insert("", tk.END, iid=note.note_id, values=(note.title, user_name, likes, comments))
    
    def on_note_select(self, event):
        """笔记选择事件"""
        selected_items = self.note_tree.selection()
        if not selected_items:
            return
        
        note_id = selected_items[0]
        
        # 查找对应的笔记
        selected_note = None
        for note in self.notes:
            if note.note_id == note_id:
                selected_note = note
                break
        
        if not selected_note:
            return
        
        # 显示笔记详情
        self.detail_text.delete(1.0, tk.END)
        
        detail_text = f"标题: {selected_note.title}\n"
        detail_text += f"用户: {selected_note.nickname}\n"
        detail_text += f"发布时间: {selected_note.upload_time}\n"
        detail_text += f"点赞数: {selected_note.liked_count}\n"
        detail_text += f"收藏数: {selected_note.collected_count}\n"
        detail_text += f"评论数: {selected_note.comment_count}\n"
        detail_text += f"分享数: {selected_note.share_count}\n"
        
        if hasattr(selected_note, "tag_list") and selected_note.tag_list:
            detail_text += f"标签: {', '.join(selected_note.tag_list)}\n"
        
        detail_text += f"\n内容:\n{selected_note.desc}\n"
        
        self.detail_text.insert(tk.END, detail_text)

def main():
    root = tk.Tk()
    app = SimpleXiaohongshuFeishuGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
