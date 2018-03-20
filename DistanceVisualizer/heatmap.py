from itertools import product
import matplotlib
matplotlib.use('Agg')
import mpld3
import sympy as sym
import matplotlib.pyplot as plt

import DistanceVisualizer.dbcontroller as dbcontroller
from DistanceVisualizer.certification_data import *
import json
import requests
import logging
import urllib3
import traceback


def get_tangential_circle(a_dist, b_dist, c_dist):
    """各RPIを中心、デバイスまでの距離を半径とした3つの円を考え、それら3円に接する最も半径の小さい円の中心座標と半径を返す"""
    x, y, R = sym.symbols('x,y,R', real=True)
    sign = [-1, 1]
    minans = (0, 0, 1000)
    for o, p, q in product(sign, sign, sign):
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
        self.data_a_list = []
        self.data_b_list = []
        self.data_c_list = []
        self.range_circle_list = []

    def push_data(self, dev_data, data_list):
        if len(data_list) == self.PI_DATA_SIZE:
            del data_list[0]
        data_list.append(dev_data)

    def put_range_circle(self, circle_data):
        if len(self.range_circle_list) == self.CIRCLE_DATA_SIZE:
            temp = self.range_circle_list[1:]
            temp.append(circle_data)
            self.range_circle_list = temp
        else:
            self.range_circle_list.append(circle_data)

    def get_moving_average_of_dist(self, data_list):
        sum = 0
        for item in data_list:
            sum += item["Dist"]
        return sum / self.PI_DATA_SIZE

    def get_moving_average_of_circle(self, data_list):
        sum_x = 0
        sum_y = 0
        sum_r = 0
        for item in data_list:
            sum_x += item[0]
            sum_y += item[1]
            sum_r += item[2]
        return sum_x / self.CIRCLE_DATA_SIZE, sum_y / self.CIRCLE_DATA_SIZE, sum_r / self.CIRCLE_DATA_SIZE

    def make_histogram(self, circle_list):
        # ドットの数
        squares = 5
        dot_per_meter = int(squares / map_range)
        x_ary = []
        y_ary = []
        min_r = 100
        for i, circle in enumerate(circle_list):
            circle_squ = [p * dot_per_meter for p in circle]
            for x_squ, y_squ in product(range(squares), range(squares)):
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


def main():
    logging.basicConfig(level=logging.DEBUG)
    map_margin = 1
    server_host = "localhost:3000"
    endpoint = "/api/distance/macaddress"
    # mysqlを直接利用する
    do_use_local_mysql = False

    devlist = []
    # テスト用デバイスのMACアドレス
    macaddresses = ("30:AE:A4:03:8A:44",)
    for i, macaddr in enumerate(macaddresses):
        devlist.append(Device(macaddr, "Device_{}".format(i + 1)))

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
                continue

            dev.push_data(data_a, dev.data_a_list)
            dev.push_data(data_b, dev.data_b_list)
            dev.push_data(data_c, dev.data_c_list)
            logging.debug("data_a_list:%s", dev.data_a_list[0])
            logging.debug("data_b_list:%s", dev.data_b_list[0])
            logging.debug("data_c_list:%s", dev.data_c_list[0])
            logging.info("#a:%s  #b:%s  #c:%s",
                         dev.get_moving_average_of_dist(dev.data_a_list),
                         dev.get_moving_average_of_dist(dev.data_b_list),
                         dev.get_moving_average_of_dist(dev.data_c_list))
            # n点で移動平均をとった距離データを元に3辺測位をする
            dev.coordinate = get_tangential_circle(
                dev.get_moving_average_of_dist(dev.data_a_list),
                dev.get_moving_average_of_dist(dev.data_b_list),
                dev.get_moving_average_of_dist(dev.data_c_list),
            )
            dev.put_range_circle(dev.coordinate)
            x, y = dev.make_histogram(dev.range_circle_list)
            plt.hist2d(x, y, bins=map_range+map_margin*2, range=[[0-map_margin, map_range+map_margin], [0-map_margin, map_range+map_margin]])
            xcoord = float(dev.get_moving_average_of_circle(dev.range_circle_list)[0])
            ycoord = float(dev.get_moving_average_of_circle(dev.range_circle_list)[1])
            plt.text(xcoord, ycoord, dev.devname, fontsize=20, color="white", weight='bold')
        plt.scatter([rpi_a_coor[0], rpi_b_coor[0], rpi_c_coor[0]], [rpi_a_coor[1], rpi_b_coor[1], rpi_c_coor[1]], s=70, c='white')
        rpi_text_mergin = 0.2
        plt.text(rpi_a_coor[0]+rpi_text_mergin, rpi_a_coor[1]+rpi_text_mergin, "RPI_A", fontsize=25, color="white", weight='heavy')
        plt.text(rpi_b_coor[0]+rpi_text_mergin, rpi_b_coor[1]+rpi_text_mergin, "RPI_B", fontsize=25, color="white", weight='heavy')
        plt.text(rpi_c_coor[0]+rpi_text_mergin, rpi_c_coor[1]+rpi_text_mergin, "RPI_C", fontsize=25, color="white", weight='heavy')
        plt.axes().set_aspect('equal', 'datalim')
        return mpld3.fig_to_html(plt.gcf())

    except KeyboardInterrupt:
        plt.close()
        conn.close()

    except requests.exceptions.ConnectionError:
        print(traceback.format_exc())
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
