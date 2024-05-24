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
scheduler = Scheduler.objects.using('default').create()
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
            return redirect('init')
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
        return HttpResponseRedirect('/off/')


def change_high(request):  # 高速
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:  # 开机才能调风速
        scheduler.change_fan_speed(room_id, 1)
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/off/')


def change_mid(request):  # 中速
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:  # 开机才能调风速
        scheduler.change_fan_speed(room_id, 2)
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/off/')


def change_low(request):  # 低速
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:  # 开机才能调风速
        scheduler.change_fan_speed(room_id, 3)
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/off/')


def change_up(request):  # 升温
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:
        temperature = room_buf.target_temp[room_id] + 1
        print(temperature)
        room_buf.target_temp[room_id] = temperature  # 先把buffer里更新
        scheduler.change_target_temp(room_id, temperature)  # 更新model里的数据库
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/off/')


def change_down(request):  # 降温
    room_id = get_room_id(request)
    if room_buf.is_on[room_id]:
        temperature = room_buf.target_temp[room_id] - 1
        room_buf.target_temp[room_id] = temperature  # 先把buffer里更新
        scheduler.change_target_temp(room_id, temperature)  # 更新model里的数据库
        return HttpResponseRedirect('/on/')
    else:
        return HttpResponseRedirect('/off/')


# ============================管理员=============================
def init(request):
    return render(request, 'init.html')


def init_submit(request):
    request.encoding = 'utf-8'
    high = int(request.GET['high'])
    low = int(request.GET['low'])
    default = int(request.GET['default'])
    fee_h = float(request.GET['fee_h'])
    fee_m = float(request.GET['fee_m'])
    fee_l = float(request.GET['fee_l'])
    for i in range(1, 6):
        room_buf.init_temp[i] = int(request.GET['r' + str(i)])

    print(room_buf.init_temp)
    scheduler.set_para(high, low, default, fee_h, fee_l, fee_m)
    scheduler.power_on()
    scheduler.start_up()
    return HttpResponseRedirect('/monitor')


def monitor(request):
    rooms = scheduler.check_room_state()
    print(rooms)
    return render(request, 'monitor.html', RoomsInfo(rooms).dic)


def tst(request):
    dic = {
        "room_id": 1,
        "state": "挂起",
        "fan_speed": "高速",
        "current_temp": 28,
        "fee": 2,
        "target_temp": 25,
        "fee_rate": 0.5
    }
    return render(request, 'monitor.html')


# ===============================前台==============================
def reception_init(request):
    return render(request, 'reception.html')


def reception(request):
    request.encoding = 'utf-8'
    room_id = request.GET['room_id']
    begin_date = request.GET['begin_date']
    end_date = request.GET['end_date']
    type = request.GET['type']
    if type == "rdr":
        # 打印详单
        # sc.print_rdr(room_id, begin_date, end_date)
        # return HttpResponseRedirect('/reception_init/')
        # 首先先生成详单
        StatisticController.print_rdr(room_id, begin_date, end_date)

        # 获取详单，返回生成的文件
        from django.http import FileResponse
        file = open('./result/detailed_list.csv', 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="detailed_list.csv"'
        return response
    else:
        # # 打印账单
        # sc.print_bill(room_id, begin_date, end_date)
        # return HttpResponseRedirect('/reception_init/')
        """打印账单"""

        # 首先先生成账单
        StatisticController.print_bill(room_id, begin_date, end_date)

        # 获取账单，返回生成的文件
        from django.http import FileResponse
        file = open('./result/bill.csv', 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="bill.csv"'
        return response


# =========================经理==========================
def manager(request):
    return render(request, "report.html")


def manager_month(request):
    month = request.GET["month"]  # 字符串，格式2020-06
    year = month.split('-')[0]
    month = month.split('-')[1]
    # *****************打印月报表**********************
    # return HttpResponseRedirect('/manager/')

    """打印月报"""
    StatisticController.draw_report(-1, 1, year, month)

    # 获取月报，返回生成的文件
    from django.http import FileResponse
    file = open('./result/report.png', 'rb')
    response = FileResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="month.png"'
    return response


def manager_week(request):
    week = request.GET["week"]  # 字符串，格式2020-W24
    #
    # # *****************打印周报表**********************
    # return HttpResponseRedirect('/manager/')
    """打印周报"""
    year = week.split('-')[0]
    week = week.split('W')[1]
    print(year)
    print(week)
    # 首先先生成周报
    StatisticController.draw_report(-1, 2, year, week)

    # 获取周报，返回生成的文件
    from django.http import FileResponse
    file = open('./result/report.png', 'rb')
    response = FileResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="week.png"'
    return response


def report_printer(request):
    room_id = request.GET['room_id']
    year = request.GET['year']
    month = request.GET['month']
    week = request.GET['week']

    if request.GET['type'] == "月报":
        """打印月报"""

        # 首先先生成月报
        StatisticController.print_report(room_id, 1, year, month)

        # 获取月报，返回生成的文件
        from django.http import FileResponse
        file = open('./result/report.csv', 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="month_report.csv"'
        return response
    else:
        """打印周报"""

        # 首先先生成周报
        StatisticController.print_report(room_id, 2, year, week)

        # 获取周报，返回生成的文件
        from django.http import FileResponse
        file = open('./result/report.csv', 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="week_report.csv"'
        return response