import requests
from datetime import datetime, timedelta
from threading import Event
import xml.dom.minidom
from jinja2 import Template

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.utils import RequestUtils, Torrent
from app.indexer.indexerConf import IndexerConf
from app.utils import ExceptionUtils, DomUtils, StringUtils

from app.plugins import EventManager
from app.plugins.modules._base import _IPluginModule
from config import Config

class Gying(_IPluginModule):
    # 插件名称
    module_name = "Gying"
    # 插件描述
    module_desc = "让内荐索引器支持检索Gying站点资源"
    # 插件图标
    module_icon = "gying.png"
    # 主题色
    module_color = "#3A88C2"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "lyxc6"
    # 作者主页
    author_url = "https://github.com/lyxc6"
    # 插件配置项ID前缀
    module_config_prefix = "gying_"
    # 加载顺序
    module_order = 20
    # 可使用的用户级别
    auth_level = 1

    _onlyonce = False
    _host = []
    _cookie = ""
    _type = "全部"



    
    # 退出事件
    _event = Event()

    @staticmethod
    def get_fields():
        return [
            {
                'type': 'div',
                'content': [
                    [
                        {
                            'title': 'Gying地址',
                            'required': '',
                            'tooltip': '一行一个Gying地址',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'gying_domain',
                                    'placeholder': 'https://www.gying.org/',
                                    'rows': 5
                                }
                        }
                    ],
                    [
                        {
                            'title': 'Cookie',
                            'required': "required",
                            'tooltip': '访问Gying的账户',
                            'type': 'password',
                            'content': [
                                {
                                    'id': 'password',
                                    'placeholder': '',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次获取索引器列表，否则需要等到预先设置的更新周期才会获取',
                            'type': 'switch',
                            'id': 'onlyonce'
                        }
                    ]
                ]
            }
        ]

    def get_state(self):
        """
        获取插件启用状态
        """

    def init_config(self, config: dict = None):
        self.eventmanager = EventManager()

        # 读取配置
        if config:
            self._host = config.get("host")
            if self._host:
                if not self._host.startswith('http'):
                    self._host = "http://" + self._host
                if self._host.endswith('/'):
                    self._host = self._host.rstrip('/')
            self._api_key = config.get("api_key")
            self._password = config.get("password")
            self._enable = self.get_status()
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            if not StringUtils.is_string_and_not_empty(self._cron):
                self._cron = "0 0 */24 * *"

        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())

            if self._cron:
                self.info(f"【{self.module_name}】 索引更新服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.get_status, CronTrigger.from_crontab(self._cron))

            if self._onlyonce:
                self.info(f"【{self.module_name}】开始获取索引器状态")
                self._scheduler.add_job(self.get_status, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())) + timedelta(
                                            seconds=3))
                # 关闭一次性开关
                self._onlyonce = False
                self.__update_config()

            if self._cron or self._onlyonce:
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            self.error(f"【{self.module_name}】停止插件错误: {str(e)}")

    def get_indexer(self):
        return indexer

    def search(self,
               keyword,
               page):
        """
        根据关键字多线程检索
        """
        if not keyword:
            return None

        self.info(f"【{self.module_name}】开始检索：{keyword} ...")
        # 特殊符号处理
        api_url = f"{indexer.domain}?apikey={self._api_key}&t=search&q={keyword}"

        result_array = self.__parse_torznabxml(api_url)

        if len(result_array) == 0:
            self.warn(f"【{self.module_name}】未检索到{keyword}数据")
            return []
        else:
            self.warn(f"【{self.module_name}】{indexer.name} 返回数据：{len(result_array)}")
            return result_array



