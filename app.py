import os
import sqlite3
import uuid
import random
from datetime import datetime, timedelta

import numpy as np

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from models.predictor import HealthPredictor

app = Flask(__name__)
CORS(app)

DB_PATH = 'eldercare.db'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, create_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS elders
                 (id TEXT PRIMARY KEY, name TEXT, age INTEGER, phone TEXT, address TEXT, remark TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS health_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, elder_id TEXT, sys_bp REAL, dia_bp REAL, 
                  blood_sugar REAL, heart_rate REAL, temperature REAL, spo2 REAL, weight REAL, 
                  measure_date TEXT, remark TEXT, create_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS service_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, elder_id TEXT, service_type TEXT, 
                  service_person TEXT, service_time TEXT, duration INTEGER, content TEXT, create_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id TEXT PRIMARY KEY, elder_id TEXT, family_id TEXT, worker_id TEXT, 
                  type TEXT, status TEXT, create_time TEXT, accept_time TEXT, remark TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, from_id TEXT, to_elder_id TEXT, 
                  content TEXT, type TEXT, create_time TEXT)''')

    c.execute("INSERT OR IGNORE INTO elders VALUES ('1001', '张爷爷', 78, '13800138001', '北京市朝阳区', '高血压')")
    c.execute("INSERT OR IGNORE INTO elders VALUES ('1002', '李奶奶', 82, '13800138002', '北京市海淀区', '糖尿病')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'admin', ?)", (datetime.now().isoformat(),))

    conn.commit()
    conn.close()
    print("✓ 数据库初始化完成")


@app.route('/')
@app.route('/<path:filename>')
def serve_static(filename='login.html'):
    return send_from_directory('.', filename)


@app.route('/api/loginByRole', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND role=?", (username, role))
    user_exists = c.fetchone()

    if not user_exists:
        conn.close()
        return jsonify({"code": 401, "msg": "该用户还未注册"})

    c.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?", (username, password, role))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({"code": 200, "data": {"username": username, "role": role, "token": str(uuid.uuid4())}})
    else:
        return jsonify({"code": 401, "msg": "密码错误"})


@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({"code": 400, "msg": "用户名已存在"})

    c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (username, password, role, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"code": 200, "msg": "注册成功"})


@app.route('/api/users', methods=['GET', 'OPTIONS'])
def get_users():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})

    role_filter = request.args.get('role', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        if role_filter:
            c.execute("SELECT username, password, role, create_time FROM users WHERE role=?", (role_filter,))
        else:
            c.execute("SELECT username, password, role, create_time FROM users")

        users = [{"username": row[0], "password": row[1], "role": row[2], "createTime": row[3]} for row in c.fetchall()]
        conn.close()
        return jsonify({"code": 200, "data": users, "msg": "获取成功"})
    except Exception as e:
        conn.close()
        return jsonify({"code": 500, "msg": str(e), "data": []})


@app.route('/api/elders', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def elders():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'GET':
        c.execute("SELECT * FROM elders ORDER BY id")
        elders = [{"id": row[0], "name": row[1], "age": row[2], "phone": row[3], "address": row[4], "remark": row[5]}
                  for row in c.fetchall()]
        conn.close()
        return jsonify({"code": 200, "data": elders})

    elif request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO elders VALUES (?, ?, ?, ?, ?, ?)",
                  (data['id'], data['name'], data['age'], data['phone'], data.get('address', ''),
                   data.get('remark', '')))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "添加成功"})

    elif request.method == 'PUT':
        data = request.json
        c.execute("UPDATE elders SET name=?, age=?, phone=?, address=?, remark=? WHERE id=?",
                  (data['name'], data['age'], data['phone'], data.get('address', ''), data.get('remark', ''),
                   data['id']))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "修改成功"})

    elif request.method == 'DELETE':
        elder_id = request.args.get('id')
        c.execute("DELETE FROM elders WHERE id=?", (elder_id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})


@app.route('/api/healthData', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def health_data():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'GET':
        elder_id = request.args.get('elder_id', '')
        if elder_id:
            c.execute("SELECT * FROM health_data WHERE elder_id=? ORDER BY measure_date DESC", (elder_id,))
        else:
            c.execute("SELECT * FROM health_data ORDER BY measure_date DESC")
        data = [{"id": row[0], "elderId": row[1], "sysBP": row[2], "diaBP": row[3], "bloodSugar": row[4],
                 "heartRate": row[5], "temperature": row[6], "spo2": row[7], "weight": row[8],
                 "measureDate": row[9], "remark": row[10]} for row in c.fetchall()]
        conn.close()
        return jsonify({"code": 200, "data": data})

    elif request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO health_data 
                     (elder_id, sys_bp, dia_bp, blood_sugar, heart_rate, temperature, spo2, weight, measure_date, remark, create_time)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data['elderId'], data.get('sysBP'), data.get('diaBP'), data.get('bloodSugar'), data.get('heartRate'),
                   data.get('temperature'), data.get('spo2'), data.get('weight'), data['measureDate'],
                   data.get('remark', ''),
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "录入成功"})

    elif request.method == 'DELETE':
        id = request.args.get('id')
        c.execute("DELETE FROM health_data WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})


@app.route('/api/serviceRecords', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def service_records():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'GET':
        c.execute("SELECT * FROM service_records ORDER BY service_time DESC")
        records = [{"id": row[0], "elderId": row[1], "serviceType": row[2], "servicePerson": row[3],
                    "serviceTime": row[4], "duration": row[5], "content": row[6]} for row in c.fetchall()]
        conn.close()
        return jsonify({"code": 200, "data": records})

    elif request.method == 'POST':
        data = request.json
        c.execute(
            "INSERT INTO service_records (elder_id, service_type, service_person, service_time, duration, content, create_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data['elderId'], data['serviceType'], data['servicePerson'], data['serviceTime'],
             data.get('duration', 30), data.get('content', ''), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "添加成功"})

    elif request.method == 'DELETE':
        id = request.args.get('id')
        c.execute("DELETE FROM service_records WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "删除成功"})

@app.route('/api/serviceRecords/all', methods=['DELETE', 'OPTIONS'])
def delete_all_service_records():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM service_records")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": f"成功删除 {deleted} 条记录", "count": deleted})
    except Exception as e:
        conn.close()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/orders', methods=['GET', 'POST', 'OPTIONS'])
def orders():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'GET':
        c.execute("SELECT * FROM orders ORDER BY create_time DESC")
        orders = [{"orderId": row[0], "elderId": row[1], "familyId": row[2], "workerId": row[3],
                   "type": row[4], "status": row[5], "createTime": row[6], "acceptTime": row[7], "remark": row[8]} for
                  row in c.fetchall()]
        conn.close()
        return jsonify({"code": 200, "data": orders})


    elif request.method == 'POST':
        data = request.json
        if data['type'] == '紧急求助':
            order_id = 'emergency' + data['elderId']
        else:
            order_id = 'escort' + data['elderId']
        c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
                  (order_id, data['elderId'], data['familyId'], '', data['type'], datetime.now().isoformat(), '',
                   data.get('remark', '')))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "订单创建成功"})


@app.route('/api/orders/accept', methods=['POST', 'OPTIONS'])
def accept_order():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE orders SET status='accepted', worker_id=?, accept_time=? WHERE order_id=?",
              (data['workerId'], datetime.now().isoformat(), data['orderId']))
    conn.commit()
    conn.close()
    return jsonify({"code": 200, "msg": "接单成功"})


@app.route('/api/orders/all', methods=['DELETE', 'OPTIONS'])
def delete_all_orders():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM orders")
        deleted_count = c.rowcount
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": f"成功删除 {deleted_count} 个订单", "count": deleted_count})
    except Exception as e:
        conn.close()
        return jsonify({"code": 500, "msg": str(e)})


@app.route('/api/messages', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def messages():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'GET':
        c.execute("SELECT * FROM messages ORDER BY create_time DESC")
        msgs = [{"id": row[0], "fromId": row[1], "toElderId": row[2], "content": row[3], "type": row[4],
                 "createTime": row[5]} for row in c.fetchall()]
        conn.close()
        return jsonify({"code": 200, "data": msgs})

    elif request.method == 'POST':
        data = request.json
        c.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                  (None, data['fromId'], data['toElderId'], data['content'], data.get('type', 'text'),
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "发送成功"})

    elif request.method == 'DELETE':
        msg_id = request.args.get('id')
        if not msg_id:
            conn.close()
            return jsonify({"code": 400, "msg": "缺少留言ID参数"})
        try:
            c.execute("SELECT * FROM messages WHERE id=?", (msg_id,))
            msg = c.fetchone()
            if not msg:
                conn.close()
                return jsonify({"code": 404, "msg": "留言不存在"})
            c.execute("DELETE FROM messages WHERE id=?", (msg_id,))
            conn.commit()
            conn.close()
            return jsonify({"code": 200, "msg": "删除成功"})
        except Exception as e:
            conn.close()
            return jsonify({"code": 500, "msg": str(e)})

@app.route('/api/messages/all', methods=['DELETE', 'OPTIONS'])
def delete_all_messages():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM messages")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": f"成功删除 {deleted} 条留言", "count": deleted})
    except Exception as e:
        conn.close()
        return jsonify({"code": 500, "msg": str(e)})

@app.route('/api/settings', methods=['POST', 'OPTIONS'])
def settings():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if 'newPassword' in data:
        c.execute("UPDATE users SET password=? WHERE username=?", (data['newPassword'], data['currentUsername']))
        conn.commit()
    conn.close()
    return jsonify({"code": 200, "msg": "修改成功"})


# ==================== AI预测接口 ====================
@app.route('/api/ai/predict/<elder_id>', methods=['GET'])
def ai_predict_health(elder_id):
    """AI健康趋势预测"""
    try:
        predictor = HealthPredictor()
        result = predictor.predict_all_indicators(elder_id)
        return jsonify({"code": 200, "data": result})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"预测失败: {str(e)}"})


@app.route('/api/ai/comprehensive/<elder_id>', methods=['GET'])
def ai_comprehensive_assessment(elder_id):
    """综合健康评估（预测+异常检测）"""
    try:
        predictor = HealthPredictor()
        prediction = predictor.predict_all_indicators(elder_id)
        anomaly = predictor.get_anomaly_detection(elder_id)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM elders WHERE id=?", (elder_id,))
        elder = c.fetchone()
        conn.close()

        return jsonify({
            "code": 200,
            "data": {
                "elder_info": {
                    "id": elder_id,
                    "name": elder[1] if elder else "未知",
                    "age": elder[2] if elder else None
                },
                "prediction": prediction,
                "anomaly_detection": anomaly,
                "assessment_time": datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"综合评估失败: {str(e)}"})


@app.route('/api/simulate/data/<elder_id>', methods=['POST', 'GET'])
def simulate_health_data(elder_id):
    """生成模拟健康数据"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM elders WHERE id=?", (elder_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({"code": 404, "msg": "老人不存在"})

    generated_count = 0

    for days_ago in range(60, 0, -1):
        measure_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

        c.execute("SELECT id FROM health_data WHERE elder_id=? AND measure_date=?", (elder_id, measure_date))
        if c.fetchone():
            continue

        base_sys = 125 if elder_id == '1001' else 130
        trend = (60 - days_ago) * 0.3

        sys_bp = round(base_sys + trend + random.uniform(-5, 5), 1)
        dia_bp = round(82 + random.uniform(-5, 5), 1)
        blood_sugar = round(5.5 + random.uniform(-1, 2.5), 1)
        heart_rate = round(75 + random.uniform(-10, 10), 1)
        temperature = round(36.5 + random.uniform(-0.3, 0.5), 1)
        spo2 = round(97 + random.uniform(-3, 2), 1)
        weight = round(65 + random.uniform(-1, 1), 1)

        c.execute('''INSERT INTO health_data 
                     (elder_id, sys_bp, dia_bp, blood_sugar, heart_rate, 
                      temperature, spo2, weight, measure_date, remark, create_time)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (elder_id, sys_bp, dia_bp, blood_sugar, heart_rate,
                   temperature, spo2, weight, measure_date, '模拟数据', datetime.now().isoformat()))
        generated_count += 1

    conn.commit()
    conn.close()

    return jsonify({"code": 200, "msg": f"成功生成{generated_count}条模拟数据"})


@app.route('/api/deleteAccount', methods=['POST', 'OPTIONS'])
def delete_account():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 验证密码
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    if not c.fetchone():
        conn.close()
        return jsonify({"code": 401, "msg": "密码错误"})

    # 删除用户
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

    return jsonify({"code": 200, "msg": "账号已注销"})
@app.route('/api/healthData/all', methods=['DELETE', 'OPTIONS'])
def delete_all_health_data():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM health_data")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": f"成功删除 {deleted} 条数据", "count": deleted})
    except Exception as e:
        conn.close()
        return jsonify({"code": 500, "msg": str(e)})

@app.route('/api/elders/all', methods=['DELETE', 'OPTIONS'])
def delete_all_elders():
    if request.method == 'OPTIONS':
        return jsonify({"code": 200})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM elders")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": f"成功删除 {deleted} 位老人", "count": deleted})
    except Exception as e:
        conn.close()
        return jsonify({"code": 500, "msg": str(e)})



# ==================== 启动 ====================
if __name__ == '__main__':
    init_db()
    os.makedirs('models', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    print("=" * 50)
    print("✓ 老人健康监护系统（含AI预测引擎）")
    print("✓ 访问地址: http://localhost:8080")
    print("✓ AI预测大屏: http://localhost:8080/ai_dashboard.html")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8080, debug=True)