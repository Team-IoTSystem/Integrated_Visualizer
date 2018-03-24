import MySQLdb


def mysql_connect(host, user, passwd, db, charset='utf8'):
    conn = MySQLdb.connect(host, user, passwd, db, charset=charset)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    return conn, cur


def select_latest(conn, cur, dev_mac, rpimac):
    cur.execute("""SELECT *
                   FROM distance AS m
                   WHERE id = (
                      SELECT MAX(id) FROM distance as s
                      WHERE s.macaddr=%s AND (s.rpimac=%s OR s.rpimac=%s)
                    )
                   """, (dev_mac, rpimac[0], rpimac[1]))
    conn.commit()
    data = cur.fetchone()
    #print("DB:{}, pwr:{}".format(data["id"], data["pwr"]))
    return data


def select_all(conn, cur, dev_mac, rpimac):
    cur.execute("""SELECT * FROM distance WHERE macaddr=%s AND rpimac=%s""", (dev_mac, rpimac))
    conn.commit()
    return cur.fetchone()