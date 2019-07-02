#! --*-- encoding: utf-8 --*--
from tornado.websocket import WebSocketHandler
from kombu.utils import json
from tornado.web import RequestHandler
import importlib
from logics import HandlerManager
from pycket.session import SessionMixin

from models import ModelBase


class BaseRequestHandler(RequestHandler, SessionMixin):
    """
    所有请求的基类
    """
    @property
    def handers(self):

        return self.request.handers

    @property
    def body(self):
        return self.request.body

    def get_current_user(self):
        current_user = self.get_secure_cookie('account')
        if current_user:
            return current_user
        return None



class APIRequestHandler(BaseRequestHandler):
    """
    全部api处理数据公共接口
    """
    def get(self):
        self.api()

    def post(self, *args, **kwargs):
        self.api()

    def initialize(self):
        self.hm = HandlerManager(self)

    def api(self):
        method_params = self.get_argument('method')
        module_name, method_name = method_params.split('.')
        try:
            module = importlib.import_module('views.%s' % module_name)
        except Exception as e:
            print(e)
            return self.result_info('error_module')
        method = getattr(module, method_name, None)
        if method is None:
            return self.result_info('err_method')

        if callable(method):
            rc, data = method(self.hm)
            if rc != 0:
                self.result_info('err', data)
            rc, data = self.result_info(rc, data)
            r = {'status':rc, 'data':data}
            result = json.dumps(r, separators=(',', ':'), encoding="utf-8",)
            try:
                self.write(result)
            finally:
                self.finish()
        return self.result_info('error_not_call_method')


    def result_info(self, rc, data=None):
        msg = ''
        if data is None:
            data = {'msg':''}
        return rc, data

class TempLateHandler(APIRequestHandler):
    """
    用来返回各种页面
    """
    def get(self):
        template = self.hm.get_argument('template', '')
        if not template:
            rc, data = 1, {'msg':'静态文件错误'}
            r = {'status': rc, 'data': data}
            result = json.dumps(r, separators=(',', ':'), encoding="utf-8", )
            self.write(result)
            self.finish()
        return TempLateHandler.render(self, template)

class IndexHandler(BaseRequestHandler):
    """
    用来返回首页
    :param BaseRequestHandler:
    :return:
    """
    def get(self):
        return IndexHandler.render(self, 'index.html')


class Myserver(WebSocketHandler, APIRequestHandler):
    all_shop_admin = dict()
    # def initialize(self):
    #     self.redis = ModelBase.get_redis_client()

    def open(self):
        print ("new client opened")
        # if not self.all_shop_admin:
        #     self.all_shop_admin = self.redis.get('all_shop_admin')
        if not self.path_args:
            self.path_args.append(self)

    def on_close(self):
        user = ''
        if self.path_kwargs:
            user = self.path_kwargs.pop('user')
        if user in self.all_shop_admin:
            self.all_shop_admin.pop(user)
            # self.redis.set('all_shop_admin', self.all_shop_admin)

    def on_message(self, message):
        print self.all_shop_admin
        if self.path_args:
            self.all_shop_admin[message] = self.path_args.pop()
            # self.redis.set('all_shop_admin', self.all_shop_admin)
            if not self.path_kwargs:
                self.path_kwargs['user'] = message
            return
        msg = message.split(':')
        account = self.path_kwargs.get('user','')
        print account, msg
        message = account + ':' + msg[0]
        account = msg[-1]
        self.__class__.send_demand_updates(message, account)


    @classmethod
    def send_demand_updates(cls, message, account):
        client = cls.all_shop_admin.get(account, '')
        if client:
            print client, '发送消息成功'
            client.write_message(message)













