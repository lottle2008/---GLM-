# AI 语音克隆与生成教育智能体 - 完整代码

## 📋 项目概述

这是一个基于智谱AI开放平台的语音克隆与生成工具，支持文生文、语音克隆、语音合成三大功能。

**技术栈**：Python 3.x + Flask + 智谱AI API + SQLite  
**端口**：7860  
**核心功能**：文生文、语音克隆、语音合成  
**双模式**：有API Key使用智谱TTS，无API Key使用系统语音

---

## 📁 项目文件清单

| 文件 | 说明 |
|------|------|
| `app.py` | 主应用程序 |
| `voices.db` | SQLite数据库（运行时自动创建） |
| `requirements.txt` | Python依赖 |
| `Dockerfile` | Docker配置 |
| `docker-compose.yml` | Docker Compose配置 |
| `run.sh` | Mac/Linux启动脚本 |
| `run.bat` | Windows启动脚本 |

---

## 📄 完整代码

### 1. app.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import sqlite3
import requests
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from queue import Queue
from threading import Thread

# 配置
API_BASE_URL = 'https://open.bigmodel.cn/api'
DB_PATH = 'voices.db'
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
task_queue = Queue()
task_results = {}

# 内置预设音色（用户已克隆好的真实音色ID）
DEFAULT_VOICES = [
    ('ea6b9f99-3bba-5e15-bf81-153b72fe1c00', '预设-klm', '卡通1-内置音色'),
    ('fedd5d14-f6e2-5968-a3d5-775b2428a886', '预设-mld', '卡通2-内置音色'),
    ('526cf8ec-d3a4-5ce8-b591-46ebc2af70ea', '预设-zhaoxue', '赵老师-内置音色')
]

def init_db():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voice_id TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0
        )
    ''')
    
    for voice_id, name, remark in DEFAULT_VOICES:
        cursor.execute('''
            INSERT OR IGNORE INTO voices (voice_id, name, remark, created_at)
            VALUES (?, ?, ?, ?)
        ''', (voice_id, name, remark, time.strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()

def get_voices_from_db(search='', page=1, per_page=10, sort_by='created_at', sort_order='desc'):
    """从数据库获取音色列表，支持搜索、分页、排序"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        default_voice_ids = [v[0] for v in DEFAULT_VOICES]
        query = 'SELECT id, voice_id, name, remark, created_at, usage_count FROM voices'
        count_query = 'SELECT COUNT(*) FROM voices'
        params = []
        
        if search:
            query = '''SELECT id, voice_id, name, remark, created_at, usage_count FROM voices
                      WHERE voice_id LIKE ? OR name LIKE ? OR remark LIKE ?'''
            count_query = '''SELECT COUNT(*) FROM voices
                            WHERE voice_id LIKE ? OR name LIKE ? OR remark LIKE ?'''
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
        
        if sort_by == 'created_at' and sort_order == 'desc':
            query += ''' ORDER BY 
                CASE WHEN voice_id IN ({}) THEN 0 ELSE 1 END,
                created_at DESC
            '''.format(','.join(['?' for _ in default_voice_ids]))
            params.extend(default_voice_ids)
        else:
            valid_sort = ['created_at', 'name', 'usage_count']
            if sort_by not in valid_sort:
                sort_by = 'created_at'
            sort_order = 'DESC' if sort_order == 'desc' else 'ASC'
            query += f' ORDER BY {sort_by} {sort_order}'
        
        offset = (page - 1) * per_page
        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        count_params = params[:-2] if search else []
        cursor.execute(count_query, count_params if search else [])
        total = cursor.fetchone()[0]
        
        conn.close()
        
        voices = [{
            'id': row[0],
            'voice_id': row[1],
            'name': row[2],
            'remark': row[3],
            'created_at': row[4],
            'usage_count': row[5]
        } for row in rows]
        
        return {
            'voices': voices,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 0
        }
    except Exception as e:
        print(f'获取音色列表失败: {str(e)}')
        return {'voices': [], 'total': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}

def save_voice_id(voice_id, name='', remark=''):
    """保存音色ID到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO voices (voice_id, name, remark, created_at)
            VALUES (?, ?, ?, ?)
        ''', (voice_id, name, remark, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'保存音色失败: {str(e)}')
        return False

def delete_voice(voice_id):
    """删除音色"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM voices WHERE voice_id = ?', (voice_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'删除音色失败: {str(e)}')
        return False

def generate_local_tts(text, voice_id):
    """本地TTS合成 - 严格对齐智谱官方7个标准音色"""
    import subprocess
    import shutil
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    filename = f'tts_{int(time.time())}.wav'
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if sys.platform == 'darwin':
        voice_map = {
            'tongtong': 'Tingting',
            'xiaochen': 'Sinji',
            'chuichui': 'Samantha',
            'jam': 'Alex',
            'kazi': 'Kathy',
            'douji': 'Tom',
            'luodo': 'Meijia'
        }
        voice = voice_map.get(voice_id, 'Tingting')
        
        try:
            print(f"[DEBUG] macOS TTS: voice_id={voice_id}, system_voice={voice}")
            
            aiff_path = filepath.replace('.wav', '.aiff')
            say_cmd = ['say', '-v', voice, '-o', aiff_path, text]
            
            result = subprocess.run(say_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[WARNING] 语音 {voice} 不可用，降级到 Tingting")
                voice = 'Tingting'
                say_cmd = ['say', '-v', voice, '-o', aiff_path, text]
                result = subprocess.run(say_cmd, capture_output=True, text=True)
            
            if not os.path.exists(aiff_path) or os.path.getsize(aiff_path) == 0:
                raise Exception(f"AIFF文件生成失败")
            
            afconvert_cmd = ['afconvert', '-f', 'WAVE', '-d', 'LEI16@22050', aiff_path, filepath]
            subprocess.run(afconvert_cmd, capture_output=True, text=True)
            
            try:
                os.remove(aiff_path)
            except:
                pass
            
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                raise Exception(f"WAV文件生成失败")
            
            return filename
        except Exception as e:
            raise Exception(f'系统语音生成失败: {str(e)}')
    
    elif sys.platform == 'win32':
        voice_map = {
            'tongtong': 'Microsoft Huihui',
            'xiaochen': 'Microsoft Yunyang',
            'chuichui': 'Microsoft Zira',
            'jam': 'Microsoft David',
            'kazi': 'Microsoft Hazel',
            'douji': 'Microsoft George',
            'luodo': 'Microsoft Xiaoxiao'
        }
        voice = voice_map.get(voice_id, 'Microsoft Huihui')
        
        try:
            print(f"[DEBUG] Windows TTS: voice_id={voice_id}, system_voice={voice}")
            
            try:
                import win32com.client
                import pythoncom
                
                pythoncom.CoInitialize()
                try:
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    temp_wav = os.path.join(OUTPUT_DIR, f'temp_{int(time.time())}.wav')
                    stream = win32com.client.Dispatch("SAPI.SpFileStream")
                    stream.Format.Type = 3
                    stream.Open(temp_wav, 3)
                    speaker.AudioOutputStream = stream
                    speaker.Speak(text)
                    stream.Close()
                    
                    if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                        shutil.move(temp_wav, filepath)
                        return filename
                    else:
                        raise Exception('SAPI生成的音频文件无效')
                finally:
                    pythoncom.CoUninitialize()
            except ImportError:
                ps_script = f'''
                Add-Type -AssemblyName System.Speech
                $synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
                $synthesizer.SetOutputToWaveFile("{filepath}")
                $synthesizer.Speak("{text.Replace('"', '`"')}")
                $synthesizer.Dispose()
                '''
                result = subprocess.run(
                    ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode != 0 or not os.path.exists(filepath):
                    raise Exception(f'PowerShell TTS失败')
                return filename
        except Exception as e:
            raise Exception(f'系统语音生成失败: {str(e)}')
    else:
        raise Exception(f'不支持的操作系统: {sys.platform}')

def call_chatglm_api(api_key, prompt):
    """调用智谱文生文API"""
    url = f'{API_BASE_URL}/paas/v4/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        'model': 'glm-4',
        'messages': [
            {'role': 'system', 'content': '你是一个专业的文案助手，擅长生成适合语音配音的文本内容。'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        raise Exception(f'API调用失败: {response.status_code}')

def clone_voice(api_key, audio_path, text):
    """调用智谱语音克隆API"""
    url = f'{API_BASE_URL}/paas/v4/audio/clone-speech'
    headers = {'Authorization': f'Bearer {api_key}'}
    
    with open(audio_path, 'rb') as f:
        files = {'audio': f}
        data = {'text': text, 'model': 'glm-tts-clone'}
        response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        return result.get('voice_id'), result.get('audio')
    else:
        raise Exception(f'克隆失败: {response.status_code}')

def process_tts_task(task):
    """处理TTS合成任务"""
    api_key = task['api_key']
    text = task['text']
    voice_id = task.get('voice_id', 'tongtong')
    mode = task.get('mode', 'api')
    
    if mode == 'system':
        filename = generate_local_tts(text, voice_id)
        return {'filename': filename}
    else:
        url = f'{API_BASE_URL}/paas/v4/audio/speech'
        params = {
            'model': 'glm-tts',
            'input': text,
            'voice': voice_id,
            'response_format': 'wav',
            'speed': 1.0,
            'volume': 1.0
        }
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        
        response = requests.post(url, headers=headers, json=params)
        if response.status_code == 200:
            filename = f'tts_{int(time.time())}.wav'
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return {'filename': filename}
        else:
            raise Exception(f'TTS失败: {response.status_code}')

def task_worker():
    """后台任务处理线程"""
    while True:
        task = task_queue.get()
        task_id = task['task_id']
        task_type = task['type']
        task_data = task['data']
        
        try:
            if task_type == 'chat':
                result = call_chatglm_api(task_data['api_key'], task_data['prompt'])
                task_results[task_id] = {'status': 'completed', 'result': result}
            elif task_type == 'clone':
                voice_id, audio_data = clone_voice(task_data['api_key'], task_data['audio_path'], task_data['text'])
                filename = f'clone_{int(time.time())}.wav'
                filepath = os.path.join(OUTPUT_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(audio_data)
                save_voice_id(voice_id, task_data.get('name', ''), task_data.get('remark', ''))
                task_results[task_id] = {'status': 'completed', 'filename': filename, 'voice_id': voice_id}
            elif task_type == 'tts':
                result = process_tts_task(task_data)
                task_results[task_id] = {'status': 'completed', **result}
        except Exception as e:
            task_results[task_id] = {'status': 'failed', 'error': str(e)}
        
        task_queue.task_done()

# 启动后台任务线程
Thread(target=task_worker, daemon=True).start()

# API路由
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/task/create', methods=['POST'])
def create_task():
    data = request.get_json()
    task_id = f'{int(time.time())}-{os.urandom(8).hex()}'
    
    if data['type'] == 'clone' and 'audio' in request.files:
        audio_file = request.files['audio']
        audio_path = os.path.join(OUTPUT_DIR, f'upload_{int(time.time())}.wav')
        audio_file.save(audio_path)
        data['data']['audio_path'] = audio_path
    
    task_queue.put({
        'task_id': task_id,
        'type': data['type'],
        'data': data['data']
    })
    
    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/task/status/<task_id>')
def get_task_status(task_id):
    result = task_results.get(task_id, {'status': 'running'})
    return jsonify(result)

@app.route('/api/voices', methods=['GET'])
def get_voices():
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    result = get_voices_from_db(search, page, per_page, sort_by, sort_order)
    return jsonify(result)

@app.route('/api/voices', methods=['POST'])
def add_voice():
    data = request.get_json()
    success = save_voice_id(data['voice_id'], data.get('name', ''), data.get('remark', ''))
    return jsonify({'success': success})

@app.route('/api/voices/<voice_id>', methods=['DELETE'])
def remove_voice(voice_id):
    success = delete_voice(voice_id)
    return jsonify({'success': success})

@app.route('/api/outputs/<filename>')
def get_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)

# 前端HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 语音克隆与生成教育智能体</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        
        .steps { display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }
        .step { background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 25px; color: white; font-weight: 500; }
        .step.active { background: white; color: #667eea; }
        
        .card { background: white; border-radius: 15px; padding: 25px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        .card-title { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        
        textarea { width: 100%; height: 120px; padding: 15px; border: 2px solid #e0e0e0; border-radius: 10px; resize: vertical; font-size: 14px; font-family: inherit; }
        textarea:focus { outline: none; border-color: #667eea; }
        
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 25px; border-radius: 10px; font-size: 14px; font-weight: 500; cursor: pointer; transition: transform 0.2s; }
        button:hover { transform: translateY(-2px); }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        
        .message { padding: 10px 15px; border-radius: 8px; margin-top: 15px; display: none; }
        .message.success { background: #d4edda; color: #155724; }
        .message.error { background: #f8d7da; color: #721c24; }
        .message.info { background: #d1ecf1; color: #0c5460; }
        
        .progress-bar { height: 6px; background: #e0e0e0; border-radius: 3px; margin-top: 15px; overflow: hidden; display: none; }
        .progress-fill { height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); animation: progress 2s infinite; }
        @keyframes progress { 0% { width: 0%; } 100% { width: 100%; } }
        
        .audio-player { width: 100%; margin-top: 15px; display: none; }
        
        .api-key-section { text-align: right; margin-bottom: 20px; }
        .api-key-btn { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 16px; border-radius: 20px; font-size: 13px; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; }
        .modal.show { display: flex; }
        .modal-content { background: white; padding: 30px; border-radius: 15px; width: 90%; max-width: 400px; }
        .modal-title { font-size: 18px; font-weight: 600; margin-bottom: 20px; }
        .modal input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; margin-bottom: 15px; font-size: 14px; }
        .modal-buttons { display: flex; gap: 10px; margin-top: 20px; }
        
        .voice-selector { margin-bottom: 20px; }
        .voice-tabs { display: flex; gap: 10px; margin-bottom: 15px; }
        .voice-tab { padding: 8px 16px; border: 2px solid #e0e0e0; border-radius: 8px; background: white; cursor: pointer; font-size: 13px; }
        .voice-tab.active { border-color: #667eea; color: #667eea; }
        
        .voice-search { margin-bottom: 15px; }
        .voice-search input { width: 100%; padding: 10px 15px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; }
        
        .voice-list { max-height: 200px; overflow-y: auto; border: 2px solid #e0e0e0; border-radius: 10px; }
        .voice-item { padding: 12px 15px; border-bottom: 1px solid #f0f0f0; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .voice-item:hover { background: #f8f9fa; }
        .voice-item.selected { background: #eef2ff; border-left: 4px solid #667eea; }
        .voice-name { font-weight: 500; }
        .voice-remark { font-size: 12px; color: #666; }
        
        .system-voice-select { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 14px; }
        
        .upload-area { border: 2px dashed #e0e0e0; border-radius: 10px; padding: 30px; text-align: center; cursor: pointer; transition: border-color 0.2s; }
        .upload-area:hover { border-color: #667eea; }
        .upload-area.dragover { border-color: #667eea; background: #f8f9ff; }
        #audioFile { display: none; }
        
        .page-controls { display: flex; justify-content: center; gap: 10px; margin-top: 15px; }
        .page-btn { padding: 8px 16px; border: 2px solid #e0e0e0; border-radius: 8px; background: white; cursor: pointer; }
        .page-btn.active { background: #667eea; color: white; border-color: #667eea; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 AI 语音克隆与生成教育智能体</h1>
            <p>基于智谱AI开放平台 | 文生文 · 语音克隆 · 语音合成</p>
        </div>
        
        <div class="api-key-section">
            <button class="api-key-btn" onclick="showApiKeyModal()" id="apiKeyBtn">API Key: 未配置</button>
        </div>
        
        <div class="steps">
            <div class="step active" id="step1">1. 文生文</div>
            <div class="step" id="step2">2. 语音克隆</div>
            <div class="step" id="step3">3. 语音合成</div>
        </div>
        
        <!-- 步骤1：文生文 -->
        <div class="card" id="card1">
            <div class="card-title">📝 文生文</div>
            <textarea id="chatInput" placeholder="输入您的文本内容，或输入生成指令让AI帮您生成..."></textarea>
            <button onclick="generateText()" id="chatBtn">
                <span>✨ AI生成文本</span>
            </button>
            <button onclick="useInputText()" style="margin-left: 10px;">
                <span>📄 使用输入文本</span>
            </button>
            <div class="message" id="chatMessage"></div>
            <div class="progress-bar" id="chatProgress">
                <div class="progress-fill"></div>
            </div>
        </div>
        
        <!-- 步骤2：语音克隆 -->
        <div class="card" id="card2">
            <div class="card-title">🎙️ 语音克隆</div>
            <div class="upload-area" id="uploadArea" onclick="document.getElementById('audioFile').click()">
                <div style="font-size: 40px; margin-bottom: 10px;">📁</div>
                <div>点击或拖拽上传参考音频（10-60秒）</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px;">支持: wav, mp3, m4a, ogg, flac</div>
            </div>
            <input type="file" id="audioFile" accept="audio/*" style="display: none;">
            <div id="audioFileName" style="margin-top: 10px; font-size: 14px; color: #666;"></div>
            <textarea id="cloneText" placeholder="请输入音频中的文本内容..."></textarea>
            <button onclick="cloneVoice()" id="cloneBtn" disabled>
                <span>🔄 开始克隆</span>
            </button>
            <div class="message" id="cloneMessage"></div>
            <div class="progress-bar" id="cloneProgress">
                <div class="progress-fill"></div>
            </div>
            <audio id="clonePlayer" class="audio-player" controls></audio>
        </div>
        
        <!-- 步骤3：语音合成 -->
        <div class="card" id="card3">
            <div class="card-title">🎧 语音合成</div>
            
            <div class="voice-tabs">
                <div class="voice-tab active" onclick="switchTtsMode('api')" id="tabApi">智谱TTS（需API Key）</div>
                <div class="voice-tab" onclick="switchTtsMode('system')" id="tabSystem">系统语音（无需API Key）</div>
            </div>
            
            <div id="apiVoiceSection">
                <div class="voice-search">
                    <input type="text" id="voiceSearch" placeholder="搜索音色...">
                </div>
                <div class="voice-list" id="voiceList"></div>
                <div class="page-controls" id="voicePageControls"></div>
            </div>
            
            <div id="systemVoiceSection" style="display: none;">
                <select class="system-voice-select" id="systemVoiceSelect">
                    <option value="tongtong">彤彤 - 中文女声</option>
                    <option value="xiaochen">小陈 - 中文男声</option>
                    <option value="chuichui">锤锤 - 英文女声</option>
                    <option value="jam">Jam - 英文男声</option>
                    <option value="kazi">Kazi - 英文女声</option>
                    <option value="douji">豆机 - 英文男声</option>
                    <option value="luodo">罗多 - 中文女声</option>
                </select>
            </div>
            
            <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 10px;">
                <div style="font-weight: 500; margin-bottom: 10px;">📄 待合成文本</div>
                <div id="ttsTextDisplay" style="font-size: 14px; line-height: 1.6; color: #666; min-height: 60px;">请先在步骤1中输入或生成文本</div>
                <textarea id="ttsText" style="display: none;"></textarea>
            </div>
            
            <button onclick="generateAudio()" id="ttsBtn">
                <span>🎧 生成音频</span>
            </button>
            <div class="message" id="ttsMessage"></div>
            <div class="progress-bar" id="ttsProgress">
                <div class="progress-fill"></div>
            </div>
            <audio id="ttsPlayer" class="audio-player" controls></audio>
        </div>
    </div>
    
    <!-- API Key配置弹窗 -->
    <div class="modal" id="apiKeyModal">
        <div class="modal-content">
            <div class="modal-title">🔑 配置API Key</div>
            <input type="password" id="apiKeyInput" placeholder="请输入智谱AI API Key">
            <div class="modal-buttons">
                <button onclick="saveApiKey()" style="flex: 1;">保存</button>
                <button onclick="closeApiKeyModal()" style="flex: 1; background: #f0f0f0; color: #333;">取消</button>
            </div>
        </div>
    </div>
    
    <!-- 音色保存弹窗 -->
    <div class="modal" id="voiceIdModal">
        <div class="modal-content">
            <div class="modal-title">💾 保存音色</div>
            <div style="margin-bottom: 15px;">
                <div style="font-size: 12px; color: #999;">音色ID</div>
                <div id="newVoiceId" style="font-family: monospace; font-size: 12px; word-break: break-all;"></div>
            </div>
            <input type="text" id="newVoiceName" placeholder="音色名称">
            <input type="text" id="newVoiceRemark" placeholder="备注说明">
            <div class="modal-buttons">
                <button onclick="saveNewVoice()" style="flex: 1;">保存</button>
                <button onclick="closeVoiceIdModal()" style="flex: 1; background: #f0f0f0; color: #333;">取消</button>
            </div>
        </div>
    </div>
    
    <script>
        let currentTtsMode = 'api';
        let selectedVoiceId = null;
        let pendingVoiceId = null;
        let currentVoicePage = 1;
        
        // 显示消息
        function showMessage(elementId, type, message) {
            const element = document.getElementById(elementId);
            element.textContent = message;
            element.className = `message ${type}`;
            element.style.display = 'block';
            setTimeout(() => { element.style.display = 'none'; }, 5000);
        }
        
        // 显示进度条
        function showProgress(elementId) {
            document.getElementById(elementId).style.display = 'block';
        }
        
        // 隐藏进度条
        function hideProgress(elementId) {
            document.getElementById(elementId).style.display = 'none';
        }
        
        // 检查API Key
        function checkApiKey() {
            const apiKey = localStorage.getItem('zhipuApiKey');
            return apiKey && apiKey.trim() !== '';
        }
        
        // 显示API Key配置弹窗
        function showApiKeyModal() {
            document.getElementById('apiKeyInput').value = localStorage.getItem('zhipuApiKey') || '';
            document.getElementById('apiKeyModal').classList.add('show');
        }
        
        // 关闭API Key配置弹窗
        function closeApiKeyModal() {
            document.getElementById('apiKeyModal').classList.remove('show');
        }
        
        // 保存API Key
        function saveApiKey() {
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            localStorage.setItem('zhipuApiKey', apiKey);
            document.getElementById('apiKeyBtn').textContent = apiKey ? 'API Key: 已配置' : 'API Key: 未配置';
            closeApiKeyModal();
            loadVoices(1);
        }
        
        // AI生成文本
        async function generateText() {
            const prompt = document.getElementById('chatInput').value.trim();
            if (!prompt) {
                showMessage('chatMessage', 'error', '请输入生成指令');
                return;
            }
            if (!checkApiKey()) {
                showMessage('chatMessage', 'error', 'AI生成需要配置API Key');
                return;
            }
            
            showProgress('chatProgress');
            showMessage('chatMessage', 'info', 'AI正在生成文本...');
            
            const taskId = await createTask('chat', {
                api_key: localStorage.getItem('zhipuApiKey'),
                prompt: prompt
            });
            
            await pollTask(taskId, (result) => {
                hideProgress('chatProgress');
                if (result.status === 'completed') {
                    showMessage('chatMessage', 'success', '文本生成成功！');
                    document.getElementById('chatInput').value = result.result;
                    updateTtsText(result.result);
                    document.getElementById('step2').classList.add('active');
                    document.getElementById('step3').classList.add('active');
                } else {
                    showMessage('chatMessage', 'error', '生成失败：' + result.error);
                }
            });
        }
        
        // 使用输入文本
        function useInputText() {
            const text = document.getElementById('chatInput').value.trim();
            if (!text) {
                showMessage('chatMessage', 'error', '请输入文本内容');
                return;
            }
            updateTtsText(text);
            showMessage('chatMessage', 'success', '文本已就绪！');
            document.getElementById('step2').classList.add('active');
            document.getElementById('step3').classList.add('active');
        }
        
        // 更新待合成文本
        function updateTtsText(text) {
            document.getElementById('ttsText').value = text;
            document.getElementById('ttsTextDisplay').textContent = text.length > 200 ? text.substring(0, 200) + '...' : text;
        }
        
        // 语音克隆
        async function cloneVoice() {
            const audioFile = document.getElementById('audioFile').files[0];
            const text = document.getElementById('cloneText').value.trim();
            
            if (!audioFile) {
                showMessage('cloneMessage', 'error', '请上传参考音频');
                return;
            }
            if (!text) {
                showMessage('cloneMessage', 'error', '请输入音频文本');
                return;
            }
            if (!checkApiKey()) {
                showMessage('cloneMessage', 'error', '语音克隆需要配置API Key');
                return;
            }
            
            showProgress('cloneProgress');
            showMessage('cloneMessage', 'info', '正在克隆语音...');
            
            const formData = new FormData();
            formData.append('audio', audioFile);
            formData.append('type', 'clone');
            formData.append('data', JSON.stringify({
                api_key: localStorage.getItem('zhipuApiKey'),
                text: text
            }));
            
            const response = await fetch('/api/task/create', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            await pollTask(result.task_id, (taskResult) => {
                hideProgress('cloneProgress');
                if (taskResult.status === 'completed') {
                    showMessage('cloneMessage', 'success', '语音克隆成功！');
                    const player = document.getElementById('clonePlayer');
                    player.src = '/api/outputs/' + taskResult.filename;
                    player.style.display = 'block';
                    player.play();
                    
                    loadVoices(1);
                    
                    if (taskResult.voice_id) {
                        pendingVoiceId = taskResult.voice_id;
                        document.getElementById('newVoiceId').textContent = taskResult.voice_id;
                        document.getElementById('newVoiceName').value = '';
                        document.getElementById('newVoiceRemark').value = '';
                        document.getElementById('voiceIdModal').classList.add('show');
                    }
                } else {
                    showMessage('cloneMessage', 'error', '克隆失败：' + taskResult.error);
                }
            });
        }
        
        // 保存新音色
        function saveNewVoice() {
            const name = document.getElementById('newVoiceName').value.trim();
            const remark = document.getElementById('newVoiceRemark').value.trim();
            
            fetch('/api/voices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    voice_id: pendingVoiceId,
                    name: name || '自定义音色',
                    remark: remark
                })
            }).then(() => {
                closeVoiceIdModal();
                loadVoices(1);
                showMessage('cloneMessage', 'success', '音色已保存！');
            });
        }
        
        // 关闭音色保存弹窗
        function closeVoiceIdModal() {
            document.getElementById('voiceIdModal').classList.remove('show');
            pendingVoiceId = null;
        }
        
        // 切换TTS模式
        function switchTtsMode(mode) {
            currentTtsMode = mode;
            document.getElementById('tabApi').className = mode === 'api' ? 'voice-tab active' : 'voice-tab';
            document.getElementById('tabSystem').className = mode === 'system' ? 'voice-tab active' : 'voice-tab';
            document.getElementById('apiVoiceSection').style.display = mode === 'api' ? 'block' : 'none';
            document.getElementById('systemVoiceSection').style.display = mode === 'system' ? 'block' : 'none';
            
            if (mode === 'api') {
                loadVoices(1);
            }
        }
        
        // 加载音色列表
        async function loadVoices(page) {
            currentVoicePage = page;
            const search = document.getElementById('voiceSearch').value;
            
            const response = await fetch(`/api/voices?page=${page}&per_page=10&search=${encodeURIComponent(search)}`);
            const result = await response.json();
            
            const voiceList = document.getElementById('voiceList');
            voiceList.innerHTML = '';
            
            result.voices.forEach(voice => {
                const item = document.createElement('div');
                item.className = `voice-item ${selectedVoiceId === voice.voice_id ? 'selected' : ''}`;
                item.onclick = () => {
                    selectedVoiceId = voice.voice_id;
                    document.querySelectorAll('.voice-item').forEach(el => el.classList.remove('selected'));
                    item.classList.add('selected');
                };
                
                const info = document.createElement('div');
                info.innerHTML = `<div class="voice-name">${voice.name || voice.voice_id}</div>`;
                if (voice.remark) {
                    info.innerHTML += `<div class="voice-remark">${voice.remark}</div>`;
                }
                
                const actions = document.createElement('div');
                actions.innerHTML = `<span style="color: #999; font-size: 12px;">使用次数: ${voice.usage_count}</span>`;
                
                item.appendChild(info);
                item.appendChild(actions);
                voiceList.appendChild(item);
            });
            
            // 更新分页控制
            const controls = document.getElementById('voicePageControls');
            controls.innerHTML = '';
            
            if (result.total_pages > 1) {
                if (page > 1) {
                    const prevBtn = document.createElement('button');
                    prevBtn.className = 'page-btn';
                    prevBtn.textContent = '上一页';
                    prevBtn.onclick = () => loadVoices(page - 1);
                    controls.appendChild(prevBtn);
                }
                
                for (let i = 1; i <= result.total_pages; i++) {
                    const btn = document.createElement('button');
                    btn.className = `page-btn ${i === page ? 'active' : ''}`;
                    btn.textContent = i;
                    btn.onclick = () => loadVoices(i);
                    controls.appendChild(btn);
                }
                
                if (page < result.total_pages) {
                    const nextBtn = document.createElement('button');
                    nextBtn.className = 'page-btn';
                    nextBtn.textContent = '下一页';
                    nextBtn.onclick = () => loadVoices(page + 1);
                    controls.appendChild(nextBtn);
                }
            }
        }
        
        // 生成音频
        async function generateAudio() {
            const text = document.getElementById('ttsText').value.trim();
            
            if (!text) {
                showMessage('ttsMessage', 'error', '请先在步骤1中输入或生成文本');
                return;
            }
            
            if (currentTtsMode === 'api') {
                if (!checkApiKey()) {
                    showMessage('ttsMessage', 'error', '智谱TTS需要配置API Key');
                    return;
                }
                if (!selectedVoiceId) {
                    showMessage('ttsMessage', 'error', '请选择一个音色');
                    return;
                }
            }
            
            showProgress('ttsProgress');
            showMessage('ttsMessage', 'info', '正在生成音频...');
            
            const taskId = await createTask('tts', {
                api_key: localStorage.getItem('zhipuApiKey'),
                text: text,
                voice_id: currentTtsMode === 'api' ? selectedVoiceId : document.getElementById('systemVoiceSelect').value,
                mode: currentTtsMode
            });
            
            await pollTask(taskId, (result) => {
                hideProgress('ttsProgress');
                if (result.status === 'completed') {
                    showMessage('ttsMessage', 'success', '音频生成成功！');
                    const player = document.getElementById('ttsPlayer');
                    player.src = '/api/outputs/' + result.filename;
                    player.style.display = 'block';
                    player.play();
                } else {
                    showMessage('ttsMessage', 'error', '生成失败：' + result.error);
                }
            });
        }
        
        // 创建任务
        async function createTask(taskType, data) {
            const response = await fetch('/api/task/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: taskType, data: data })
            });
            const result = await response.json();
            return result.task_id;
        }
        
        // 轮询任务状态
        async function pollTask(taskId, callback) {
            const interval = setInterval(async () => {
                const response = await fetch(`/api/task/status/${taskId}`);
                const result = await response.json();
                
                if (result.status === 'completed' || result.status === 'failed') {
                    clearInterval(interval);
                    callback(result);
                }
            }, 1000);
        }
        
        // 音频文件上传处理
        document.getElementById('audioFile').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('audioFileName').textContent = `已选择: ${file.name}`;
                document.getElementById('cloneBtn').disabled = false;
            }
        });
        
        // 拖拽上传处理
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('audio/')) {
                document.getElementById('audioFile').files = e.dataTransfer.files;
                document.getElementById('audioFileName').textContent = `已选择: ${file.name}`;
                document.getElementById('cloneBtn').disabled = false;
            }
        });
        
        // 初始化
        document.addEventListener('DOMContentLoaded', () => {
            const apiKey = localStorage.getItem('zhipuApiKey');
            document.getElementById('apiKeyBtn').textContent = apiKey ? 'API Key: 已配置' : 'API Key: 未配置';
            loadVoices(1);
            
            // ESC关闭弹窗
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    closeApiKeyModal();
                    closeVoiceIdModal();
                }
            });
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # 清理端口
    try:
        import subprocess
        if sys.platform == 'darwin' or sys.platform == 'linux':
            subprocess.run(['lsof', '-ti:7860'], capture_output=True)
            subprocess.run(['kill', '-9', '7860'], capture_output=True)
    except:
        pass
    
    init_db()
    print('🚀 AI语音克隆与生成教育智能体启动中...')
    print('📡 访问地址: http://localhost:7860')
    app.run(host='0.0.0.0', port=7860, debug=False)
```

---

### 2. requirements.txt

```txt
Flask==3.1.3
requests==2.31.0
pyinstaller==6.10.0
pywin32>=306; sys_platform == 'win32'
```

### 3. Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 7860

CMD ["python", "app.py"]
```

### 4. docker-compose.yml

```yaml
version: '3.8'

services:
  zhipu-audio:
    build: .
    ports:
      - "7860:7860"
    volumes:
      - ./outputs:/app/outputs
      - ./voices.db:/app/voices.db
    restart: unless-stopped
```

### 5. run.sh (Mac/Linux)

```bash
#!/bin/bash
echo "🎤 启动AI语音克隆与生成教育智能体..."

# 清理端口
lsof -ti:7860 | xargs kill -9 2>/dev/null
sleep 1

# 检查Python
if command -v python3 &>/dev/null; then
    python3 app.py
elif command -v python &>/dev/null; then
    python app.py
else
    echo "❌ 未找到Python，请安装Python 3.7+"
    exit 1
fi
```

### 6. run.bat (Windows)

```batch
@echo off
echo 启动AI语音克隆与生成教育智能体...

:: 清理端口
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860') do taskkill /f /pid %%a

:: 启动服务
python app.py
```

---

## 🚀 快速开始

### 方式一：直接运行

```bash
# 克隆仓库
git clone https://github.com/lottle2008/---GLM-.git
cd ZW tts-clone

# 安装依赖
pip install -r requirements.txt

# 启动服务
python3 app.py
```

### 方式二：Docker部署

```bash
# 使用docker-compose
docker-compose up -d

# 或手动构建
docker build -t zhipu-audio .
docker run -p 7860:7860 zhipu-audio
```

### 方式三：启动脚本

```bash
# Mac/Linux
chmod +x run.sh
./run.sh

# Windows
run.bat
```

---

## 📖 使用指南

### 1. 配置API Key（可选）

1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/) 注册账号
2. 获取API Key
3. 在应用界面点击右上角"API Key: 未配置"按钮
4. 输入API Key并保存

### 2. 文生文

- **AI生成**：输入生成指令，点击"AI生成文本"
- **手动输入**：直接输入文本，点击"使用输入文本"

### 3. 语音克隆（需要API Key）

1. 上传10-60秒的参考音频
2. 输入音频对应的文本
3. 点击"开始克隆"
4. 克隆成功后自动保存到音色库

### 4. 语音合成

- **智谱TTS模式**：选择音色库中的音色
- **系统语音模式**：选择系统内置音色（无需API Key）
- 点击"生成音频"

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_BASE_URL` | 智谱API地址 | https://open.bigmodel.cn/api |
| `PORT` | 服务端口 | 7860 |

### 内置预设音色

| ID | 名称 | 说明 |
|----|------|------|
| ea6b9f99-3bba-5e15-bf81-153b72fe1c00 | 预设-klm | 卡通1-内置音色 |
| fedd5d14-f6e2-5968-a3d5-775b2428a886 | 预设-mld | 卡通2-内置音色 |
| 526cf8ec-d3a4-5ce8-b591-46ebc2af70ea | 预设-zhaoxue | 赵老师-内置音色 |

### 系统语音映射

| 音色ID | 中文名称 | macOS | Windows |
|--------|----------|-------|---------|
| tongtong | 彤彤 | Tingting | Microsoft Huihui |
| xiaochen | 小陈 | Sinji | Microsoft Yunyang |
| chuichui | 锤锤 | Samantha | Microsoft Zira |
| jam | Jam | Alex | Microsoft David |
| kazi | Kazi | Kathy | Microsoft Hazel |
| douji | 豆机 | Tom | Microsoft George |
| luodo | 罗多 | Meijia | Microsoft Xiaoxiao |

---

## 📁 项目结构

```
ZW tts-clone/
├── app.py                 # 主应用程序
├── voices.db             # SQLite数据库（运行时创建）
├── outputs/              # 音频输出目录（运行时创建）
├── requirements.txt       # Python依赖
├── Dockerfile            # Docker配置
├── docker-compose.yml    # Docker Compose配置
├── run.sh               # Mac/Linux启动脚本
├── run.bat              # Windows启动脚本
└── README.md            # 项目说明
```

---

## 🛠️ 技术栈

- **Python 3.7+** - 核心开发语言
- **Flask 3.1.3** - Web框架
- **SQLite** - 本地数据库
- **Requests** - HTTP客户端
- **PyInstaller** - 打包工具

---

## 📞 技术支持

如有问题，请提交Issue到GitHub仓库。

---

*文档最后更新：2026年5月21日*