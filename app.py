from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os
import subprocess
import socket
import glob

app = Flask(__name__)
app.secret_key = 'honeyduo-secret-key-2024'

app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True


# Configuration
ROM_DIR = '/home/honeyduopi/Desktop/HoneyDuoGaming/N64'
RETROARCH_CONFIG = os.path.expanduser('~/.config/retroarch')
CORE_PATH = os.path.join(RETROARCH_CONFIG, 'cores/mupen64plus_next_libretro.so')
STATES_DIR = os.path.join(RETROARCH_CONFIG, 'states/Mupen64Plus-Next')
CHEATS_DIR = os.path.join(RETROARCH_CONFIG, 'cheats/Mupen64Plus-Next')
CHEATS_DB_DIR = os.path.join(RETROARCH_CONFIG, 'cheats/N64')
GAME_CONFIGS_DIR = os.path.join(RETROARCH_CONFIG, 'config/Mupen64Plus-Next')
PASSWORD = 'Togetheralways5$'

# Ensure directories exist
for d in [STATES_DIR, CHEATS_DIR, GAME_CONFIGS_DIR]:
    os.makedirs(d, exist_ok=True)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def send_retroarch_cmd(cmd):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(cmd.encode(), ('127.0.0.1', 55355))
        sock.close()
        return True
    except:
        return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/n64')
@login_required
def n64():
    games = []
    for ext in ['*.z64', '*.n64', '*.v64']:
        for f in glob.glob(os.path.join(ROM_DIR, ext)):
            name = os.path.splitext(os.path.basename(f))[0]
            games.append({'name': name, 'file': os.path.basename(f)})
    games.sort(key=lambda x: x['name'])
    return render_template('n64.html', games=games)

@app.route('/api/launch', methods=['POST'])
@login_required
def launch_game():
    game = request.json.get('game')
    if not game:
        return jsonify({'status': 'error', 'message': 'No game specified'}), 400
    rom_path = os.path.join(ROM_DIR, game)
    if not os.path.exists(rom_path):
        return jsonify({'status': 'error', 'message': 'Game not found'}), 404
    env = os.environ.copy()
    env['DISPLAY'] = ':0'
    env['XDG_RUNTIME_DIR'] = '/run/user/1000'
    env['PULSE_SERVER'] = 'unix:/run/user/1000/pulse/native'
    subprocess.Popen(['/usr/bin/retroarch', '-f', '-L', CORE_PATH, rom_path], env=env, start_new_session=True)
    return jsonify({'status': 'launched'})

@app.route('/api/stop', methods=['POST'])
@login_required
def stop_game():
    subprocess.run(['/usr/bin/pkill', '-9', '-f', 'retroarch'], capture_output=True)
    return jsonify({'status': 'stopped'})

@app.route('/api/status')
@login_required
def game_status():
    result = subprocess.run(['/usr/bin/pgrep', '-f', 'retroarch'], capture_output=True)
    return jsonify({'running': result.returncode == 0})

@app.route('/api/states/<game>')
@login_required
def get_states(game):
    game_name = os.path.splitext(game)[0]
    states = []
    for ext in ['.state', '.state1', '.state2', '.state3', '.state4', '.state5', '.state6', '.state7', '.state8', '.state9']:
        pattern = os.path.join(STATES_DIR, f'{game_name}{ext}*')
        for f in glob.glob(pattern):
            if not f.endswith('.png'):
                slot = '0' if f.endswith('.state') else f.split('.state')[-1]
                states.append({'file': os.path.basename(f), 'slot': slot, 'modified': os.path.getmtime(f)})
    states.sort(key=lambda x: int(x['slot']))
    return jsonify(states)

@app.route('/api/states/<game>/<slot>', methods=['DELETE'])
@login_required
def delete_state(game, slot):
    game_name = os.path.splitext(game)[0]
    ext = '.state' if slot == '0' else f'.state{slot}'
    state_path = os.path.join(STATES_DIR, f'{game_name}{ext}')
    if os.path.exists(state_path):
        os.remove(state_path)
        png_path = state_path + '.png'
        if os.path.exists(png_path):
            os.remove(png_path)
        return jsonify({'status': 'deleted'})
    return jsonify({'status': 'not found'}), 404

@app.route('/api/savestate', methods=['POST'])
@login_required
def save_state():
    slot = request.json.get('slot', 0)
    send_retroarch_cmd(f'STATE_SLOT {slot}')
    import time
    time.sleep(0.1)
    send_retroarch_cmd('SAVE_STATE')
    return jsonify({'status': 'saved', 'slot': slot})

@app.route('/api/loadstate', methods=['POST'])
@login_required
def load_state():
    slot = request.json.get('slot', 0)
    send_retroarch_cmd(f'STATE_SLOT {slot}')
    import time
    time.sleep(0.1)
    send_retroarch_cmd('LOAD_STATE')
    return jsonify({'status': 'loaded', 'slot': slot})

@app.route('/api/settings/<game>')
@login_required
def get_settings(game):
    game_name = os.path.splitext(game)[0]
    config_path = os.path.join(GAME_CONFIGS_DIR, f'{game_name}.cfg')
    settings = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, val = line.strip().split('=', 1)
                    settings[key.strip()] = val.strip().strip('"')
    return jsonify(settings)

@app.route('/api/settings/<game>', methods=['POST'])
@login_required
def save_settings(game):
    game_name = os.path.splitext(game)[0]
    config_path = os.path.join(GAME_CONFIGS_DIR, f'{game_name}.cfg')
    settings = request.json
    with open(config_path, 'w') as f:
        for key, val in settings.items():
            f.write(f'{key} = "{val}"\n')
    return jsonify({'status': 'saved'})

# Database routes MUST come before generic <game> routes
@app.route('/api/cheats/database/<game>')
@login_required
def get_database_cheats(game):
    game_name = os.path.splitext(game)[0]
    cheat_path = os.path.join(CHEATS_DB_DIR, f'{game_name}.cht')
    
    if not os.path.exists(cheat_path):
        search_term = game_name.split('(')[0].strip().lower()
        for f in os.listdir(CHEATS_DB_DIR):
            if search_term in f.lower():
                cheat_path = os.path.join(CHEATS_DB_DIR, f)
                break
    
    cheats = []
    if os.path.exists(cheat_path):
        current_cheat = {}
        with open(cheat_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('cheat') and '_desc' in line:
                    if current_cheat and 'desc' in current_cheat:
                        cheats.append(current_cheat)
                    current_cheat = {'desc': line.split('=', 1)[1].strip().strip('"'), 'enabled': False, 'code': ''}
                elif '_enable' in line and current_cheat:
                    current_cheat['enabled'] = 'true' in line.lower()
                elif '_code' in line and current_cheat:
                    current_cheat['code'] = line.split('=', 1)[1].strip().strip('"')
            if current_cheat and 'desc' in current_cheat:
                cheats.append(current_cheat)
    return jsonify({'cheats': cheats, 'source': os.path.basename(cheat_path) if os.path.exists(cheat_path) else None})

@app.route('/api/cheats/<game>/import', methods=['POST'])
@login_required
def import_cheats(game):
    game_name = os.path.splitext(game)[0]
    cheat_path = os.path.join(CHEATS_DIR, f'{game_name}.cht')
    
    existing_cheats = []
    if os.path.exists(cheat_path):
        current_cheat = {}
        with open(cheat_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('cheat') and '_desc' in line:
                    if current_cheat and 'desc' in current_cheat:
                        existing_cheats.append(current_cheat)
                    current_cheat = {'desc': line.split('=', 1)[1].strip().strip('"'), 'enabled': False, 'code': ''}
                elif '_enable' in line and current_cheat:
                    current_cheat['enabled'] = 'true' in line.lower()
                elif '_code' in line and current_cheat:
                    current_cheat['code'] = line.split('=', 1)[1].strip().strip('"')
            if current_cheat and 'desc' in current_cheat:
                existing_cheats.append(current_cheat)
    
    existing_codes = {c['code'] for c in existing_cheats}
    new_cheats = request.json.get('cheats', [])
    for cheat in new_cheats:
        if cheat['code'] not in existing_codes:
            existing_cheats.append({'desc': cheat['desc'], 'code': cheat['code'], 'enabled': True})
    
    with open(cheat_path, 'w') as f:
        f.write(f'cheats = {len(existing_cheats)}\n\n')
        for i, cheat in enumerate(existing_cheats):
            f.write(f'cheat{i}_desc = "{cheat["desc"]}"\n')
            f.write(f'cheat{i}_code = "{cheat["code"]}"\n')
            f.write(f'cheat{i}_enable = {"true" if cheat.get("enabled") else "false"}\n\n')
    
    return jsonify({'status': 'imported', 'total': len(existing_cheats)})

@app.route('/api/cheats/<game>/add', methods=['POST'])
@login_required
def add_cheat(game):
    game_name = os.path.splitext(game)[0]
    cheat_path = os.path.join(CHEATS_DIR, f'{game_name}.cht')
    new_cheat = request.json
    
    cheats = []
    if os.path.exists(cheat_path):
        current_cheat = {}
        with open(cheat_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('cheat') and '_desc' in line:
                    if current_cheat and 'desc' in current_cheat:
                        cheats.append(current_cheat)
                    current_cheat = {'desc': line.split('=', 1)[1].strip().strip('"'), 'enabled': False, 'code': ''}
                elif '_enable' in line and current_cheat:
                    current_cheat['enabled'] = 'true' in line.lower()
                elif '_code' in line and current_cheat:
                    current_cheat['code'] = line.split('=', 1)[1].strip().strip('"')
            if current_cheat and 'desc' in current_cheat:
                cheats.append(current_cheat)
    
    cheats.append({'desc': new_cheat.get('desc', 'New Cheat'), 'code': new_cheat.get('code', ''), 'enabled': new_cheat.get('enabled', False)})
    
    with open(cheat_path, 'w') as f:
        f.write(f'cheats = {len(cheats)}\n\n')
        for i, cheat in enumerate(cheats):
            f.write(f'cheat{i}_desc = "{cheat["desc"]}"\n')
            f.write(f'cheat{i}_code = "{cheat["code"]}"\n')
            f.write(f'cheat{i}_enable = {"true" if cheat.get("enabled") else "false"}\n\n')
    
    return jsonify({'status': 'added'})

@app.route('/api/cheats/<game>/<int:index>', methods=['DELETE'])
@login_required
def delete_cheat(game, index):
    game_name = os.path.splitext(game)[0]
    cheat_path = os.path.join(CHEATS_DIR, f'{game_name}.cht')
    
    cheats = []
    if os.path.exists(cheat_path):
        current_cheat = {}
        with open(cheat_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('cheat') and '_desc' in line:
                    if current_cheat and 'desc' in current_cheat:
                        cheats.append(current_cheat)
                    current_cheat = {'desc': line.split('=', 1)[1].strip().strip('"'), 'enabled': False, 'code': ''}
                elif '_enable' in line and current_cheat:
                    current_cheat['enabled'] = 'true' in line.lower()
                elif '_code' in line and current_cheat:
                    current_cheat['code'] = line.split('=', 1)[1].strip().strip('"')
            if current_cheat and 'desc' in current_cheat:
                cheats.append(current_cheat)
    
    if 0 <= index < len(cheats):
        cheats.pop(index)
        with open(cheat_path, 'w') as f:
            f.write(f'cheats = {len(cheats)}\n\n')
            for i, cheat in enumerate(cheats):
                f.write(f'cheat{i}_desc = "{cheat["desc"]}"\n')
                f.write(f'cheat{i}_code = "{cheat["code"]}"\n')
                f.write(f'cheat{i}_enable = {"true" if cheat.get("enabled") else "false"}\n\n')
        return jsonify({'status': 'deleted'})
    return jsonify({'status': 'error'}), 404

@app.route('/api/cheats/<game>', methods=['GET'])
@login_required
def get_cheats(game):
    game_name = os.path.splitext(game)[0]
    cheat_path = os.path.join(CHEATS_DIR, f'{game_name}.cht')
    cheats = []
    if os.path.exists(cheat_path):
        current_cheat = {}
        with open(cheat_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('cheat') and '_desc' in line:
                    if current_cheat and 'desc' in current_cheat:
                        cheats.append(current_cheat)
                    idx = line.split('_')[0].replace('cheat', '')
                    current_cheat = {'index': idx, 'desc': line.split('=', 1)[1].strip().strip('"'), 'enabled': False, 'code': ''}
                elif '_enable' in line and current_cheat:
                    current_cheat['enabled'] = 'true' in line.lower()
                elif '_code' in line and current_cheat:
                    current_cheat['code'] = line.split('=', 1)[1].strip().strip('"')
            if current_cheat and 'desc' in current_cheat:
                cheats.append(current_cheat)
    return jsonify(cheats)

@app.route('/api/cheats/<game>', methods=['POST'])
@login_required
def save_cheats(game):
    game_name = os.path.splitext(game)[0]
    cheat_path = os.path.join(CHEATS_DIR, f'{game_name}.cht')
    cheats = request.json
    with open(cheat_path, 'w') as f:
        f.write(f'cheats = {len(cheats)}\n\n')
        for i, cheat in enumerate(cheats):
            f.write(f'cheat{i}_desc = "{cheat["desc"]}"\n')
            f.write(f'cheat{i}_code = "{cheat["code"]}"\n')
            f.write(f'cheat{i}_enable = {"true" if cheat.get("enabled") else "false"}\n\n')
    return jsonify({'status': 'saved'})

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('/home/honeyduopi/Desktop/HoneyDuoGaming/static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
