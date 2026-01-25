from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.lang import Builder
import threading
import time
import uiautomator2 as u2
import json
import os

# 配置文件路径
CONFIG_FILE = 'ad_close_config.json'

# 默认配置
DEFAULT_CONFIG = {
    'close_button_texts': ["关闭", "取消", "跳过", "×", "X", "close", "Cancel", "Skip"],
    'close_button_ids': [
        "com.android.systemui:id/close",
        "com.android.systemui:id/button1",
        "android:id/button1",
        "android:id/closeButton"
    ],
    'detection_interval': 0.1,  # 检测间隔（秒）
    'connection_timeout': 5,  # 设备连接超时（秒）
    'click_delay': 0.1,  # 点击后的延迟（秒）
    'log_max_lines': 100  # 最大日志行数
}

# 加载KV语言定义
Builder.load_string('''
<AdCloseApp>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    BoxLayout:
        size_hint_y: None
        height: 50
        spacing: 10

        Button:
            id: start_btn
            text: '开始检测'
            on_press: root.start_detection()
            background_color: 0, 0.7, 0, 1

        Button:
            id: stop_btn
            text: '停止检测'
            on_press: root.stop_detection()
            disabled: True
            background_color: 0.7, 0, 0, 1

    BoxLayout:
        size_hint_y: None
        height: 40
        spacing: 10

        Label:
            text: '检测状态:'
            size_hint_x: 0.2

        Label:
            id: status_label
            text: '就绪'
            color: 0, 0, 1, 1
            size_hint_x: 0.8

    ScrollView:
        size_hint_y: 1

        TextInput:
            id: log_output
            text: '日志输出：'
            readonly: True
            multiline: True
            font_size: 14
            text_size: self.width, None
            height: max(self.minimum_height, self.parent.height)
''')

class ConfigManager:
    """配置管理类"""
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value
        return self.save_config()

class AdCloseApp(BoxLayout):
    def __init__(self, **kwargs):
        super(AdCloseApp, self).__init__(**kwargs)
        self.detection_thread = None
        self.running = False
        self.device = None
        self.config_manager = ConfigManager()
        
        # 从配置加载参数
        self.close_button_texts = self.config_manager.get('close_button_texts', DEFAULT_CONFIG['close_button_texts'])
        self.close_button_ids = self.config_manager.get('close_button_ids', DEFAULT_CONFIG['close_button_ids'])
        self.detection_interval = self.config_manager.get('detection_interval', DEFAULT_CONFIG['detection_interval'])
        self.connection_timeout = self.config_manager.get('connection_timeout', DEFAULT_CONFIG['connection_timeout'])
        self.click_delay = self.config_manager.get('click_delay', DEFAULT_CONFIG['click_delay'])
        self.log_max_lines = self.config_manager.get('log_max_lines', DEFAULT_CONFIG['log_max_lines'])
        
        self.log("应用启动，配置加载完成")
        self.log(f"检测间隔: {self.detection_interval}秒")
    
    def log(self, message):
        """添加日志信息"""
        timestamp = time.strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        # 添加新日志
        current_log = self.ids.log_output.text
        new_log = log_entry + current_log
        
        # 限制日志行数
        lines = new_log.strip().split('\n')
        if len(lines) > self.log_max_lines:
            new_log = '\n'.join(lines[:self.log_max_lines]) + '\n'
        
        # 更新日志显示
        self.ids.log_output.text = new_log
        
        # 滚动到底部
        def scroll_to_bottom(dt):
            self.ids.log_output.cursor = (0, len(new_log))
        Clock.schedule_once(scroll_to_bottom, 0.1)
    
    def update_status(self, status, color=(1, 1, 1, 1)):
        """更新状态显示"""
        self.ids.status_label.text = status
        self.ids.status_label.color = color
    
    def start_detection(self):
        """开始检测广告"""
        self.log("开始检测广告...")
        self.update_status("运行中", (0, 1, 0, 1))
        self.ids.start_btn.disabled = True
        self.ids.stop_btn.disabled = False
        self.running = True
        
        # 在新线程中运行检测逻辑
        self.detection_thread = threading.Thread(target=self.detect_ads)
        self.detection_thread.daemon = True
        self.detection_thread.start()
    
    def stop_detection(self):
        """停止检测广告"""
        self.log("停止检测广告...")
        self.running = False
        self.update_status("已停止", (1, 0, 0, 1))
        self.ids.start_btn.disabled = False
        self.ids.stop_btn.disabled = True
        
        if self.detection_thread:
            self.detection_thread.join(timeout=2.0)
    
    def detect_ads(self):
        """检测并关闭广告"""
        try:
            # 连接设备（这里使用本地连接，因为脚本将在设备上运行）
            self.log("正在连接设备...")
            self.update_status("连接中", (1, 1, 0, 1))
            
            # 尝试连接设备
            start_time = time.time()
            while time.time() - start_time < self.connection_timeout:
                try:
                    self.device = u2.connect('localhost')
                    self.log("设备连接成功！")
                    self.update_status("运行中", (0, 1, 0, 1))
                    break
                except Exception as e:
                    time.sleep(0.5)
                    if time.time() - start_time >= self.connection_timeout:
                        raise
            
            # 确保设备已连接
            if not self.device:
                raise Exception("设备连接失败")
            
            # 检测循环
            while self.running:
                try:
                    # 遍历查找关闭按钮
                    found = self.find_and_close_ad()
                    
                    # 短暂延迟，避免过于频繁的检测
                    time.sleep(self.detection_interval)
                    
                except Exception as e:
                    self.log(f"检测过程中出错: {str(e)}")
                    time.sleep(1.0)  # 出错后延迟1秒
                    
        except Exception as e:
            self.log(f"错误: {str(e)}")
            self.update_status("错误", (1, 0, 0, 1))
            self.stop_detection()
    
    def find_and_close_ad(self):
        """查找并关闭广告"""
        # 按文本查找（包含用户提供的所有关闭按钮文本）
        for text in self.close_button_texts:
            try:
                if self.device(text=text).exists(timeout=0.05):
                    self.log(f"发现广告关闭按钮: {text}")
                    self.device(text=text).click()
                    time.sleep(self.click_delay)  # 点击后延迟
                    return True
            except Exception as e:
                # 忽略单个查找失败
                pass
        
        # 按资源ID查找
        for resource_id in self.close_button_ids:
            try:
                if self.device(resourceId=resource_id).exists(timeout=0.05):
                    self.log(f"发现广告关闭按钮 (ID): {resource_id}")
                    self.device(resourceId=resource_id).click()
                    time.sleep(self.click_delay)  # 点击后延迟
                    return True
            except Exception as e:
                # 忽略单个查找失败
                pass
        
        # 按描述查找
        try:
            if self.device(description="关闭").exists(timeout=0.05):
                self.log("发现广告关闭按钮 (描述): 关闭")
                self.device(description="关闭").click()
                time.sleep(self.click_delay)  # 点击后延迟
                return True
        except Exception as e:
            # 忽略查找失败
            pass
        
        # 额外的查找方法：按类名查找常见的关闭按钮
        try:
            if self.device(className="android.widget.Button").exists(timeout=0.05):
                buttons = self.device(className="android.widget.Button")
                for button in buttons:
                    try:
                        text = button.text
                        if text in self.close_button_texts:
                            self.log(f"发现广告关闭按钮 (类名): {text}")
                            button.click()
                            time.sleep(self.click_delay)  # 点击后延迟
                            return True
                    except Exception:
                        pass
        except Exception as e:
            # 忽略查找失败
            pass
        
        return False

class AdCloseAppGUI(App):
    def build(self):
        return AdCloseApp()

if __name__ == '__main__':
    AdCloseAppGUI().run()