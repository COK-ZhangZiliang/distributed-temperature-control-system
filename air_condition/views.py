import numpy as np
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from air_condition.models import Scheduler, StatisticController


# Create your views here.

# ===============类================
class RoomCounter:  # 分配房间号
    num = 0  # 当前已有房间数
    dic = {}  # session_id: room_id,目的是每个session对应一个房间号


class RoomInfo:  # Room->字典
    dic = {
        "target_temp": "--",
        "init_temp": "--",
        "current_temp": "--",
        "fan_speed": "--",
        "fee": 0,
        "room_id": 0
    }

    def __init__(self, room):
        self.dic["target_temp"] = room.target_temp
        self.dic["init_temp"] = room.init_temp
        self.dic["current_temp"] = int(room.current_temp)
        self.dic["fan_speed"] = speed_ch[room.fan_speed]
        self.dic["fee"] = int(room.fee)
        self.dic["room_id"] = room.room_id


class RoomsInfo:  # 监控器使用
    def __init__(self, rooms):
        self.dic = {
            "room_id": [0],
            "state": [""],
            "fan_speed": [""],
            "current_temp": [0],
            "fee": [0],
            "target_temp": [0],
            "fee_rate": [0]
        }
        if rooms:
            for room in rooms:  # 从1号房开始
                self.dic["room_id"].append(room.room_id)
                self.dic["state"].append(state_ch[room.state])
                self.dic["fan_speed"].append(speed_ch[room.fan_speed])
                self.dic["current_temp"].append('%.2f' % room.current_temp)
                self.dic["fee"].append('%.2f' % room.fee)
                self.dic["target_temp"].append(room.target_temp)
                self.dic["fee_rate"].append(room.fee_rate)


class RoomBuffer:  # 房间数据缓存,下标从1开始
    is_on = [None, False, False, False, False, False]  # 房间是否开机,开机为True
    target_temp = [0, 25, 25, 25, 25, 25]  # 目标温度,默认25
    init_temp = [0, 32, 28, 30, 29, 35]  # 初始温度,也是户外温度


class ChartData:
    open_time = []  # 五个房间的开机时长
    record_num = 0  # 详单数
    schedule_num = 0  # 调度次数
    open_num = []  # 五个房间的*开机次数*
    change_temp_num = []  # 五个房间的调温次数
    change_fan_num = []  # 五个房间的调风速次数
    # ---numpy---
    fee = np.zeros([6, 30])  # 五个房间，30分钟内费用 + 30分钟内总费用


# ============静态变量===========
room_c = RoomCounter  # 静态
room_info = RoomInfo
scheduler = Scheduler()  # 属于model模块
sc = StatisticController
room_buf = RoomBuffer
speed_ch = ["", "高速", "中速", "低速"]
state_ch = ["", "服务中", "等待", "关机", "休眠"]


# ===============================


# ================函数 <顾客界面>  ==============
def get_room_id(request):
    s_id = request.session.session_key  # 获取session_id, 无则创建
    if s_id is None:
        request.session.create()
        s_id = request.session.session_key

    if s_id not in room_c.dic:  # 未分配房间号
        room_c.num = room_c.num + 1
        room_c.dic[s_id] = room_c.num
        return room_c.num
    else:
        return room_c.dic[s_id]


def log_in(request):  # 用户登录界面
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        usertype = 0

        with open('air_condition/user.txt', 'r') as file:
            # 逐行读取文件
            for line in file:
                # 使用split()方法按空格分割每行
                columns = line.strip().split()  # strip()去除行首尾的空白字符

                if username == columns[0]:
                    if password == columns[1]:
                        usertype = columns[2]

        if usertype == "1":
            return redirect('client_off')
        elif usertype == "2":
            pass
        elif usertype == "3":
            pass
        else:
            # 如果凭据无效，返回登录页面并显示错误信息
            return render(request, 'log-in.html', {'error': 'Invalid username or password'})

    return render(request, 'log-in.html')


def client_off(request):  # 第一次访问客户端界面
    room_id = get_room_id(request)
    room = scheduler.update_room_state(room_id)
    if room:  # -----------之所以要判断，是因为第一次访问页面，room有未创建的风险
        return render(request, 'client-off.html', RoomInfo(room).dic)
    else:  # 没有room实例
        return render(request, 'client-off.html', room_info.dic)


def client_on(request):  # 开机后的界面
    room_id = get_room_id(request)
    room = scheduler.update_room_state(room_id)
    return render(request, 'client-on.html', RoomInfo(room).dic)


def power(request):  # 开关机
    room_id = get_room_id(request)
    # 从buf里获取房间状态,关机变开机，开机变关机
    if not room_buf.is_on[room_id]:
        room_buf.is_on[room_id] = True
        scheduler.request_on(room_id, room_buf.init_temp[room_id])
        scheduler.set_init_temp(room_id, room_buf.init_temp[room_id])
        return HttpResponseRedirect('/on/')
    else:
        room_buf.is_on[room_id] = False
        scheduler.request_off(room_id)
        return HttpResponseRedirect('/')


def change_high(request):  # 高速
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:  # 开机才能调风速
        scheduler.change_fan_speed(room_id, 1)
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/')


def change_mid(request):  # 中速
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:  # 开机才能调风速
        scheduler.change_fan_speed(room_id, 2)
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/')


def change_low(request):  # 低速
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:  # 开机才能调风速
        scheduler.change_fan_speed(room_id, 3)
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/')


def change_up(request):  # 升温
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:
        temperature = room_buf.target_temp[room_id] + 1
        room_buf.target_temp[room_id] = temperature  # 先把buffer里更新
        scheduler.change_target_temp(room_id, temperature)  # 更新model里的数据库
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/')


def change_down(request):  # 降温
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:
        temperature = room_buf.target_temp[room_id] - 1
        room_buf.target_temp[room_id] = temperature  # 先把buffer里更新
        scheduler.change_target_temp(room_id, temperature)  # 更新model里的数据库
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/')
