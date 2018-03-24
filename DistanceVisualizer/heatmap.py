from itertools import product
from collections import deque
from logging import getLogger, StreamHandler, DEBUG, INFO
import DistanceVisualizer.dbcontroller as dbcontroller
from DistanceVisualizer.certification_data import *

import matplotlib
matplotlib.use('Agg')
import requests
import mpld3
import sympy as sym
import matplotlib.pyplot as plt


def get_tangential_circle(a_dist, b_dist, c_dist):
    """各RPIを中心、デバイスまでの距離を半径とした3つの円を考え、それら3円に接する最も半径の小さい円の中心座標と半径を返す"""
    x, y, R = sym.symbols('x,y,R', real=True)
    sign = [-1, 1]
    minans = (0, 0, 1000)
    for o, p, q in product(sign, repeat=3):
        result = sym.solve([(x - rpi_a_coor[0]) ** 2 + (y - rpi_a_coor[1]) ** 2 - (R + o * a_dist) ** 2,
                            (x - rpi_b_coor[0]) ** 2 + (y - rpi_b_coor[1]) ** 2 - (R + p * b_dist) ** 2,
                            (x - rpi_c_coor[0]) ** 2 + (y - rpi_c_coor[1]) ** 2 - (R + q * c_dist) ** 2], [x, y, R])
        for ans in result:
            if 0 < ans[2] < minans[2]:
                minans = ans
    return minans[0], minans[1], minans[2]


def get_latest_data(server_host, endpoint, dev_macaddr, rpi_macaddr):
    dist = "http://" + server_host + endpoint
    payload = {"macaddress": dev_macaddr, "rpi_macaddress": rpi_macaddr, "new_order_one": 1}
    return requests.get(dist, params=payload)


class Device:
    PI_DATA_SIZE = 3
    CIRCLE_DATA_SIZE = 3

    def __init__(self, macaddr, devname):
        self.macaddr = macaddr
        self.devname = devname
        self.data_a_queue = deque(maxlen=self.PI_DATA_SIZE)
        self.data_b_queue = deque(maxlen=self.PI_DATA_SIZE)
        self.data_c_queue = deque(maxlen=self.PI_DATA_SIZE)
        self.range_circle_queue = deque(maxlen=self.CIRCLE_DATA_SIZE)

    @staticmethod
    def push_data(dev_data, data_queue):
        data_queue.append(dev_data)

    def put_range_circle(self, circle_data):
        self.range_circle_queue.append(circle_data)

    def get_moving_average_of_dist(self, data_queue):
        sum = 0
        for item in data_queue:
            sum += item["Dist"]
        return sum / self.PI_DATA_SIZE

    def get_moving_average_of_circle(self, data_queue):
        sum_x = 0
        sum_y = 0
        sum_r = 0
        for item in data_queue:
            sum_x += item[0]
            sum_y += item[1]
            sum_r += item[2]
        return sum_x / self.CIRCLE_DATA_SIZE, sum_y / self.CIRCLE_DATA_SIZE, sum_r / self.CIRCLE_DATA_SIZE

    @staticmethod
    def make_histogram(circle_queue):
        # ドットの数
        squares = 5
        dot_per_meter = int(squares / map_range)
        x_ary = []
        y_ary = []
        min_r = 100
        for circle in circle_queue:
            circle_squ = [p * dot_per_meter for p in circle]
            for x_squ, y_squ in product(range(squares), repeat=2):
                r = (x_squ - circle_squ[0]) ** 2 + (y_squ - circle_squ[1]) ** 2
                if r <= circle_squ[2] ** 2:
                    x_ary.append(x_squ / dot_per_meter)
                    y_ary.append(y_squ / dot_per_meter)
                if r <= circle_squ[2] / 2:
                    x_ary.append(x_squ / dot_per_meter)
                    y_ary.append(y_squ / dot_per_meter)
                if r < min_r:
                    x_min = x_squ
                    y_min = y_squ
                    min_r = r
        if not x_ary or not y_ary:
            x_ary.append(x_min)
            y_ary.append(y_min)
        return x_ary, y_ary

devlist = []
# テスト用デバイスのMACアドレス
macaddresses = ("30:AE:A4:03:8A:44",)
for i, macaddr in enumerate(macaddresses):
    devlist.append(Device(macaddr, "Device_{}".format(i + 1)))


def main():
    global devlist
    logger = getLogger(__name__)
    logger.setLevel(DEBUG)
    if not logger.handlers:
        handler = StreamHandler()
        handler.setLevel(DEBUG)
        logger.addHandler(handler)
    logger.propagate = False
    map_margin = 1
    server_host = "localhost:3000"
    endpoint = "/api/distance/macaddress"
    # mysqlを直接利用する
    do_use_local_mysql = False

    if do_use_local_mysql:
        conn, cur = dbcontroller.mysql_connect(host, user, passwd, db)

    try:
        plt.clf()
        for dev in devlist:
            if do_use_local_mysql:
                data_a = dbcontroller.select_latest(conn, cur, dev.macaddr, rpi_a_mac)
                data_b = dbcontroller.select_latest(conn, cur, dev.macaddr, rpi_b_mac)
                data_c = dbcontroller.select_latest(conn, cur, dev.macaddr, rpi_c_mac)
            else:
                data_a = get_latest_data(server_host, endpoint, dev.macaddr, rpi_a_mac).json()[0]
                data_b = get_latest_data(server_host, endpoint, dev.macaddr, rpi_b_mac).json()[0]
                data_c = get_latest_data(server_host, endpoint, dev.macaddr, rpi_c_mac).json()[0]
            if (data_a and data_b and data_c) is None:
                logger.error('cannot get distance data')
                continue

            dev.push_data(data_a, dev.data_a_queue)
            dev.push_data(data_b, dev.data_b_queue)
            dev.push_data(data_c, dev.data_c_queue)
            logger.debug("data_a_queue:%s", dev.data_a_queue[0])
            logger.debug("data_b_queue:%s", dev.data_b_queue[0])
            logger.debug("data_c_queue:%s", dev.data_c_queue[0])
            logger.info(
                "#a:%f  #b:%f  #c:%f",
                dev.get_moving_average_of_dist(dev.data_a_queue),
                dev.get_moving_average_of_dist(dev.data_b_queue),
                dev.get_moving_average_of_dist(dev.data_c_queue)
            )
            # n点で移動平均をとった距離データを元に3辺測位をする
            dev.coordinate = get_tangential_circle(
                dev.get_moving_average_of_dist(dev.data_a_queue),
                dev.get_moving_average_of_dist(dev.data_b_queue),
                dev.get_moving_average_of_dist(dev.data_c_queue),
            )
            dev.put_range_circle(dev.coordinate)
            x, y = dev.make_histogram(dev.range_circle_queue)
            plt.hist2d(x, y, bins=map_range+map_margin*2, range=[[0-map_margin, map_range+map_margin], [0-map_margin, map_range+map_margin]])
            xcoord = float(dev.get_moving_average_of_circle(dev.range_circle_queue)[0])
            ycoord = float(dev.get_moving_average_of_circle(dev.range_circle_queue)[1])
            plt.text(xcoord, ycoord, dev.devname, fontsize=20, color="white", weight='bold')
        plt.scatter([rpi_a_coor[0], rpi_b_coor[0], rpi_c_coor[0]], [rpi_a_coor[1], rpi_b_coor[1], rpi_c_coor[1]], s=70, c='white')
        rpi_text_margin = 0.2
        plt.text(rpi_a_coor[0]+rpi_text_margin, rpi_a_coor[1]+rpi_text_margin, "RPI_A", fontsize=25, color="white", weight='heavy')
        plt.text(rpi_b_coor[0]+rpi_text_margin, rpi_b_coor[1]+rpi_text_margin, "RPI_B", fontsize=25, color="white", weight='heavy')
        plt.text(rpi_c_coor[0]+rpi_text_margin, rpi_c_coor[1]+rpi_text_margin, "RPI_C", fontsize=25, color="white", weight='heavy')
        plt.axes().set_aspect('equal', 'datalim')
        return mpld3.fig_to_html(plt.gcf())

    except KeyboardInterrupt:
        plt.close()
        conn.close()

    except requests.exceptions.ConnectionError:
        logger.exception("Couldn't receive data from API server")
        return None


# 各RPIの座標
rpi_a_coor = [0, 0]
rpi_b_coor = [0, 5]
rpi_c_coor = [3.5, 2.5]

# ヒートマップ表示範囲[m]
map_range = 5

# 各RPIのmacaddr
rpi_a_mac = "b827ebe98ea9", "3476c58b5506"
rpi_b_mac = "b827ebf277a4", "3476c58b5522"
rpi_c_mac = "b827ebb63034", "106f3f59c177"


# # ダミーデータ
# data_a = {"id": 6, "macaddr": "AA:BB:CC:DD:EE", "pwr": -42, "distance": 2, "rpimac": "rpi_a"}

if __name__ == "__main__":
    main()