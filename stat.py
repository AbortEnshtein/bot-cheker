#!/usr/bin/env python3
# tor_web_monitor.py - Веб-интерфейс для мониторинга Tor прокси

import os
import time
import threading
import subprocess
from datetime import datetime
from flask import Flask, jsonify, render_template_string

# ================= НАСТРОЙКИ =================
CONTROL_PORT = 9051
CONTROL_PASSWORD = "МОЙ_СУПЕР_ПАРОЛЬ"  # ЗАМЕНИТЕ НА ВАШ ПАРОЛЬ!
PROXY_PORT = 9050
FLASK_PORT = 8080
FLASK_HOST = "0.0.0.0"
# ============================================

app = Flask(__name__)

# Кэш для статистики
stats_cache = {
    'connections': 0,
    'clients': [],
    'circuits': 0,
    'streams': 0,
    'tor_version': 'N/A',
    'uptime': 0,
    'traffic_in': 0,
    'traffic_out': 0,
    'last_update': None
}

def get_tor_stats():
    """Получает статистику через ControlPort"""
    try:
        from stem.control import Controller
        from stem import Signal
        
        with Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate(CONTROL_PASSWORD)
            
            # Базовая информация
            tor_version = controller.get_info('version', 'N/A')
            
            # Статус и аптайм
            uptime = controller.get_info('uptime', 0)
            
            # Активные цепи (circuits)
            circuits = controller.get_circuits()
            active_circuits = len([c for c in circuits if c.status == 'BUILT'])
            
            # Активные потоки (streams)
            streams = controller.get_streams()
            active_streams = len([s for s in streams if s.status == 'SUCCEEDED'])
            
            return {
                'tor_version': tor_version,
                'uptime': int(float(uptime)) if uptime != 'N/A' else 0,
                'circuits': active_circuits,
                'streams': active_streams
            }
    except Exception as e:
        return {'error': str(e)}

def get_connection_stats():
    """Получает статистику TCP подключений к прокси"""
    try:
        # Количество активных соединений
        result = subprocess.run(
            f"ss -tn state established | grep -c :{PROXY_PORT}",
            shell=True, capture_output=True, text=True
        )
        connections = int(result.stdout.strip() or 0)
        
        # Уникальные IP клиентов
        result = subprocess.run(
            f"ss -tn state established | grep :{PROXY_PORT} | awk '{{print $4}}' | cut -d: -f1 | sort | uniq -c",
            shell=True, capture_output=True, text=True
        )
        
        clients = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.strip().split()
                if len(parts) == 2:
                    clients.append({'ip': parts[1], 'connections': int(parts[0])})
        
        return connections, clients
    except Exception as e:
        return 0, []

def get_traffic_stats():
    """Получает статистику трафика через порт"""
    try:
        # Используем /proc/net/dev для примерной оценки
        with open('/proc/net/dev', 'r') as f:
            for line in f:
                if 'eth0' in line or 'ens' in line:
                    parts = line.split()
                    if len(parts) >= 10:
                        rx = int(parts[1])  # получено байт
                        tx = int(parts[9])  # отправлено байт
                        return rx, tx
        return 0, 0
    except:
        return 0, 0

def update_stats():
    """Фоновый поток для обновления статистики"""
    while True:
        tor_stats = get_tor_stats()
        connections, clients = get_connection_stats()
        rx, tx = get_traffic_stats()
        
        stats_cache['connections'] = connections
        stats_cache['clients'] = clients
        stats_cache['circuits'] = tor_stats.get('circuits', 0)
        stats_cache['streams'] = tor_stats.get('streams', 0)
        stats_cache['tor_version'] = tor_stats.get('tor_version', 'N/A')
        stats_cache['uptime'] = tor_stats.get('uptime', 0)
        stats_cache['traffic_in'] = rx
        stats_cache['traffic_out'] = tx
        stats_cache['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        time.sleep(3)  # Обновление каждые 3 секунды

def format_bytes(bytes_val):
    """Форматирует байты в читаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_uptime(seconds):
    """Форматирует аптайм в читаемый вид"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м"
    else:
        return f"{minutes}м"

# HTML шаблон для веб-интерфейса
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="5">
    <meta charset="UTF-8">
    <title>Tor Proxy Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
            color: #00d4ff;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .card h3 {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 10px;
            color: #aaa;
        }
        .card .value {
            font-size: 36px;
            font-weight: bold;
            color: #00d4ff;
        }
        .card .unit {
            font-size: 14px;
            color: #888;
        }
        .clients-table {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
        }
        .clients-table h3 {
            margin-bottom: 15px;
            color: #00d4ff;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th {
            color: #aaa;
            font-weight: normal;
        }
        .status-online {
            color: #00ff88;
        }
        .status-offline {
            color: #ff4444;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            font-size: 12px;
            color: #666;
        }
        .warning {
            background: rgba(255,100,0,0.2);
            border: 1px solid #ff6400;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>📡 Tor Proxy Monitor</h1>
    
    <div class="stats-grid">
        <div class="card">
            <h3>Активные подключения</h3>
            <div class="value">{{ stats.connections }}</div>
        </div>
        <div class="card">
            <h3>Уникальные клиенты</h3>
            <div class="value">{{ stats.clients_count }}</div>
        </div>
        <div class="card">
            <h3>Tor circuits</h3>
            <div class="value">{{ stats.circuits }}</div>
        </div>
        <div class="card">
            <h3>Tor streams</h3>
            <div class="value">{{ stats.streams }}</div>
        </div>
        <div class="card">
            <h3>Входящий трафик</h3>
            <div class="value">{{ stats.traffic_in }}</div>
        </div>
        <div class="card">
            <h3>Исходящий трафик</h3>
            <div class="value">{{ stats.traffic_out }}</div>
        </div>
    </div>
    
    <div class="clients-table">
        <h3>🖥️ Подключенные клиенты</h3>
        {% if stats.clients %}
        <table>
            <tr>
                <th>IP-адрес</th>
                <th>Активных соединений</th>
            </tr>
            {% for client in stats.clients %}
            <tr>
                <td>{{ client.ip }}</td>
                <td>{{ client.connections }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>Нет активных подключений</p>
        {% endif %}
    </div>
    
    <div class="clients-table">
        <h3>ℹ️ Информация о сервере</h3>
        <table>
            <tr><td>Версия Tor</td><td>{{ stats.tor_version }}</td></tr>
            <tr><td>Аптайм Tor</td><td>{{ stats.uptime }}</td></tr>
            <tr><td>Порт прокси</td><td>{{ stats.proxy_port }}</td></tr>
            <tr><td>Последнее обновление</td><td>{{ stats.last_update }}</td></tr>
        </table>
    </div>
    
    <div class="footer">
        Tor Proxy Monitor | ControlPort: {{ stats.control_port }}
    </div>
</div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, stats={
        'connections': stats_cache['connections'],
        'clients': stats_cache['clients'],
        'clients_count': len(stats_cache['clients']),
        'circuits': stats_cache['circuits'],
        'streams': stats_cache['streams'],
        'tor_version': stats_cache['tor_version'],
        'uptime': format_uptime(stats_cache['uptime']),
        'traffic_in': format_bytes(stats_cache['traffic_in']),
        'traffic_out': format_bytes(stats_cache['traffic_out']),
        'proxy_port': PROXY_PORT,
        'control_port': CONTROL_PORT,
        'last_update': stats_cache['last_update'] or 'Никогда'
    })

@app.route('/api/stats')
def api_stats():
    """JSON API для получения статистики"""
    return jsonify({
        'connections': stats_cache['connections'],
        'clients': stats_cache['clients'],
        'circuits': stats_cache['circuits'],
        'streams': stats_cache['streams'],
        'tor_version': stats_cache['tor_version'],
        'uptime': stats_cache['uptime'],
        'last_update': stats_cache['last_update']
    })

def main():
    print("=" * 50)
    print("🚀 Запуск Tor Proxy Monitor")
    print("=" * 50)
    print(f"📡 Веб-интерфейс: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"🔌 Порт прокси: {PROXY_PORT}")
    print(f"🎮 ControlPort: {CONTROL_PORT}")
    print("=" * 50)
    print("Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    # Запускаем фоновый поток для обновления статистики
    thread = threading.Thread(target=update_stats, daemon=True)
    thread.start()
    
    # Запускаем Flask
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)

if __name__ == '__main__':
    main()