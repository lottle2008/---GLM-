#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智谱AI 语音克隆 Web 应用
跨平台本地服务，支持 Windows 和 Mac
功能顺序：文生文 → 语音克隆 → 语音合成
"""

import os
import sys
import time
import json
import requests
import sqlite3
import uuid
import threading
import subprocess
from queue import Queue
from flask import Flask, render_template_string, request, jsonify, send_from_directory
import webbrowser

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

API_BASE_URL = 'https://open.bigmodel.cn/api'
SYSTEM_VOICES = ['tongtong', 'chuichui', 'xiaochen', 'jam', 'kazi', 'douji', 'luodo']

def get_app_data_dir():
    """获取应用数据目录（跨平台）"""
    if sys.platform == 'win32':
        return os.path.join(os.environ.get('APPDATA', ''), 'ZhipuAudio')
    elif sys.platform == 'darwin':
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'ZhipuAudio')
    else:
        return os.path.join(os.path.expanduser('~'), '.ZhipuAudio')

# 使用resource_path获取正确的路径（支持PyInstaller打包）
BASE_DIR = os.path.dirname(resource_path('.'))
OUTPUT_DIR = os.path.join(get_app_data_dir(), 'outputs')
DB_PATH = os.path.join(get_app_data_dir(), 'voices.db')

# 确保输出目录存在
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    
# 确保数据库目录存在（实际上已经由OUTPUT_DIR创建了）

# 异步任务队列
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

def save_voice_to_db(voice_id, name='', remark=''):
    """保存音色到数据库"""
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
        print(f'保存音色到数据库失败: {str(e)}')
        return False

def get_voices_from_db(search='', page=1, per_page=10, sort_by='created_at', sort_order='desc'):
    """从数据库获取音色列表，支持搜索、分页、排序
    内置预设音色始终在最前面，其他音色按时间倒序
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 内置预设音色ID列表
        default_voice_ids = [v[0] for v in DEFAULT_VOICES]
        
        # 构建查询
        query = 'SELECT id, voice_id, name, remark, created_at, usage_count FROM voices'
        count_query = 'SELECT COUNT(*) FROM voices'
        params = []
        
        if search:
            query = '''SELECT id, voice_id, name, remark, created_at, usage_count FROM voices
                      WHERE voice_id LIKE ? OR name LIKE ? OR remark LIKE ?'''
            count_query = '''SELECT COUNT(*) FROM voices
                            WHERE voice_id LIKE ? OR name LIKE ? OR remark LIKE ?'''
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
        
        # 排序：内置预设音色优先，其他按时间倒序
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
        
        # 获取总数
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

def update_voice_remark(voice_id, remark):
    """更新音色备注"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE voices SET remark = ? WHERE voice_id = ?', (remark, voice_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'更新音色备注失败: {str(e)}')
        return False

def update_voice_name(voice_id, name):
    """更新音色名称"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE voices SET name = ? WHERE voice_id = ?', (name, voice_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'更新音色名称失败: {str(e)}')
        return False

def increment_voice_usage(voice_id):
    """增加音色使用次数"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE voices SET usage_count = usage_count + 1 WHERE voice_id = ?', (voice_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f'更新音色使用次数失败: {str(e)}')
        return False

def delete_voice_from_db(voice_id):
    """从数据库删除音色"""
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
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    filename = f'tts_{int(time.time())}.wav'
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 官方标准音色映射到系统语音
    # 智谱官方7个音色：tongtong(彤彤)、xiaochen(小陈)、chuichui(锤锤)、jam(Jam)、kazi(Kazi)、douji(豆机)、luodo(罗多)
    if sys.platform == 'darwin':
        # macOS系统语音映射
        voice_map = {
            'tongtong': 'Tingting',     # 彤彤 -> 婷婷(中文女声)
            'xiaochen': 'Sinji',         # 小陈 -> 善怡(粤语,作为男声替代)
            'chuichui': 'Samantha',     # 锤锤 -> Samantha(英文女声)
            'jam': 'Alex',               # Jam -> Alex(英文男声)
            'kazi': 'Kathy',             # Kazi -> Kathy(英文女声)
            'douji': 'Tom',              # 豆机 -> Tom(英文男声)
            'luodo': 'Meijia'            # 罗多 -> 美佳(台湾普通话女声)
        }
        
        voice = voice_map.get(voice_id, 'Tingting')
        
        try:
            print(f"[DEBUG] macOS TTS: voice_id={voice_id}, system_voice={voice}, text_length={len(text)}")
            
            aiff_path = filepath.replace('.wav', '.aiff')
            
            # 构建say命令 - macOS say命令格式: say -v <voice> -o <output.aiff> <text>
            say_cmd = ['say', '-v', voice, '-o', aiff_path, text]
            
            print(f"[DEBUG] 执行命令: {' '.join(say_cmd)}")
            
            # 执行say命令
            result = subprocess.run(say_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                print(f"[ERROR] say命令失败: {error_msg}")
                
                # 尝试不带输出文件的方式测试语音是否可用
                test_result = subprocess.run(['say', '-v', voice, '测试'], capture_output=True, text=True)
                if test_result.returncode != 0:
                    # 语音不可用，降级到默认语音
                    print(f"[WARNING] 语音 {voice} 不可用，降级到 Tingting")
                    voice = 'Tingting'
                    say_cmd = ['say', '-v', voice, '-o', aiff_path, text]
                    result = subprocess.run(say_cmd, capture_output=True, text=True)
            
            # 检查AIFF文件是否生成成功
            if not os.path.exists(aiff_path) or os.path.getsize(aiff_path) == 0:
                raise Exception(f"AIFF文件生成失败: {aiff_path}")
            
            print(f"[DEBUG] AIFF文件生成成功: {aiff_path}")
            
            # 使用afconvert转换为WAV格式
            afconvert_cmd = ['afconvert', '-f', 'WAVE', '-d', 'LEI16@22050', aiff_path, filepath]
            result = subprocess.run(afconvert_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[WARNING] afconvert转换失败，直接复制AIFF文件")
                shutil.copy(aiff_path, filepath)
            
            # 删除临时AIFF文件
            try:
                os.remove(aiff_path)
            except Exception as e:
                print(f"[WARNING] 删除临时文件失败: {e}")
            
            # 验证最终WAV文件
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                raise Exception(f"WAV文件生成失败或为空: {filepath}")
            
            print(f"[DEBUG] WAV文件生成成功: {filepath}")
            return filename
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            print(f"[ERROR] subprocess调用失败: {error_msg}")
            raise Exception(f'系统语音生成失败: {error_msg}')
        except Exception as e:
            print(f"[ERROR] 系统语音生成异常: {str(e)}")
            raise Exception(f'系统语音生成失败: {str(e)}')
    
    elif sys.platform == 'win32':
        # Windows系统语音映射
        # Windows SAPI支持的中文语音: 微软慧慧, 微软晓晓, 微软小云, 微软小娜等
        voice_map = {
            'tongtong': 'Microsoft Huihui',     # 彤彤 -> 微软慧慧(中文女声)
            'xiaochen': 'Microsoft Yunyang',    # 小陈 -> 微软云扬(中文男声)
            'chuichui': 'Microsoft Zira',       # 锤锤 -> Zira(英文女声)
            'jam': 'Microsoft David',           # Jam -> David(英文男声)
            'kazi': 'Microsoft Hazel',          # Kazi -> Hazel(英文女声)
            'douji': 'Microsoft George',        # 豆机 -> George(英文男声)
            'luodo': 'Microsoft Xiaoxiao'       # 罗多 -> 微软晓晓(中文女声)
        }
        
        voice = voice_map.get(voice_id, 'Microsoft Huihui')
        
        try:
            print(f"[DEBUG] Windows TTS: voice_id={voice_id}, system_voice={voice}, text_length={len(text)}")
            
            # 优先使用win32com
            try:
                import win32com.client
                import pythoncom
                
                pythoncom.CoInitialize()
                try:
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    
                    # 设置语音
                    voices = speaker.GetVoices()
                    found_voice = None
                    for i in range(voices.Count):
                        v = voices.Item(i)
                        v_desc = v.GetDescription()
                        if voice.lower() in v_desc.lower():
                            found_voice = v
                            break
                    
                    if found_voice:
                        speaker.Voice = found_voice
                        print(f"[DEBUG] 找到语音: {found_voice.GetDescription()}")
                    else:
                        print(f"[WARNING] 未找到语音 {voice}，使用默认语音")
                    
                    # 创建临时WAV文件
                    temp_wav = os.path.join(OUTPUT_DIR, f'temp_{int(time.time())}.wav')
                    
                    stream = win32com.client.Dispatch("SAPI.SpFileStream")
                    stream.Format.Type = 3  # SPCAT_WAVEFORM
                    stream.Open(temp_wav, 3)  # 3 = SSFMCreateForWrite
                    speaker.AudioOutputStream = stream
                    
                    print(f"[DEBUG] 开始语音合成...")
                    speaker.Speak(text)
                    print(f"[DEBUG] 语音合成完成")
                    
                    stream.Close()
                    
                    # 验证并移动文件
                    if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                        shutil.move(temp_wav, filepath)
                        print(f"[DEBUG] WAV文件生成成功: {filepath}")
                        return filename
                    else:
                        raise Exception(f'SAPI生成的音频文件无效或为空: {temp_wav}')
                        
                finally:
                    pythoncom.CoUninitialize()
                    
            except ImportError:
                # 降级到PowerShell方案
                print(f"[DEBUG] win32com不可用，使用PowerShell方案")
                
                # PowerShell脚本 - 使用语音名称匹配
                ps_script = f'''
                Add-Type -AssemblyName System.Speech
                $synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
                
                # 尝试选择指定语音
                $targetVoice = "{voice}"
                $selectedVoice = $synthesizer.GetInstalledVoices() | Where-Object {{ 
                    $_.VoiceInfo.Name -like "*$targetVoice*"
                }}
                
                if ($selectedVoice) {{
                    $synthesizer.SelectVoice($selectedVoice.VoiceInfo.Name)
                    Write-Host "使用语音: $($selectedVoice.VoiceInfo.Name)"
                }} else {{
                    Write-Host "未找到语音 $targetVoice，使用默认语音"
                }}
                
                # 设置输出格式并合成
                $synthesizer.SetOutputToWaveFile("{filepath}")
                $synthesizer.Speak("{text.Replace('"', '`"')}")
                $synthesizer.Dispose()
                '''
                
                result = subprocess.run(
                    ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode('utf-8', errors='ignore') or result.stdout
                    print(f"[ERROR] PowerShell TTS失败: {error_msg}")
                    raise Exception(f'PowerShell TTS失败: {error_msg}')
                
                if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                    raise Exception(f'PowerShell生成的音频文件无效或为空')
                
                print(f"[DEBUG] PowerShell WAV文件生成成功: {filepath}")
                return filename
                
        except Exception as e:
            print(f"[ERROR] Windows TTS异常: {str(e)}")
            raise Exception(f'系统语音生成失败: {str(e)}')
    
    else:
        # Linux或其他系统
        print(f"[ERROR] 不支持的操作系统: {sys.platform}")
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
            {'role': 'system', 'content': '你是一个专业的文案助手，擅长生成适合语音配音的文本内容。请根据用户的需求生成自然、流畅的配音文本。'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        try:
            error_msg = response.json().get('error', {}).get('message', str(response.status_code))
        except:
            error_msg = f'HTTP {response.status_code}'
        raise Exception(f'文生文API调用失败: {error_msg}')

def async_task_worker():
    """异步任务处理线程"""
    while True:
        task = task_queue.get()
        if task is None:
            break
        
        task_id = task['task_id']
        task_type = task['task_type']
        try:
            if task_type == 'clone':
                result = process_clone_task(task)
            elif task_type == 'tts':
                result = process_tts_task(task)
            elif task_type == 'chat':
                result = process_chat_task(task)
            
            task_results[task_id] = {'status': 'completed', **result}
        except Exception as e:
            task_results[task_id] = {'status': 'error', 'error': str(e)}
        
        task_queue.task_done()

def process_clone_task(task):
    """处理语音克隆任务"""
    api_key = task['api_key']
    audio_path = task['audio_path']
    text = task['text']
    sample_text = task.get('sample_text', '')
    
    headers = {'Authorization': f'Bearer {api_key}'}
    
    # 上传音频文件
    upload_url = f'{API_BASE_URL}/paas/v4/files'
    files = {'file': open(audio_path, 'rb')}
    upload_data = {'purpose': 'voice-clone-input'}
    upload_response = requests.post(upload_url, headers=headers, files=files, data=upload_data)
    upload_response.raise_for_status()
    file_id = upload_response.json()['id']
    
    # 执行克隆
    clone_url = f'{API_BASE_URL}/paas/v4/voice/clone'
    voice_name = f'voice_{int(time.time())}'
    clone_params = {
        'model': 'glm-tts-clone',
        'voice_name': voice_name,
        'input': text,
        'file_id': file_id,
        'request_id': f'req_{int(time.time())}'
    }
    if sample_text:
        clone_params['text'] = sample_text
    
    clone_response = requests.post(clone_url, headers={**headers, 'Content-Type': 'application/json'}, json=clone_params)
    clone_response.raise_for_status()
    clone_result = clone_response.json()
    
    # 下载结果
    preview_file_id = clone_result['file_id']
    download_url = f'{API_BASE_URL}/paas/v4/files/{preview_file_id}/content'
    download_response = requests.get(download_url, headers=headers)
    download_response.raise_for_status()
    
    filename = f'clone_{int(time.time())}.wav'
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(download_response.content)
    
    # 清理临时文件
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    voice_id = clone_result.get('voice', '')
    if voice_id:
        save_voice_to_db(voice_id, voice_name, '')
    
    return {'filename': filename, 'voice_id': voice_id}

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
            
            if voice_id != 'tongtong':
                increment_voice_usage(voice_id)
            
            return {'filename': filename}
        else:
            try:
                error_msg = response.json().get('error', {}).get('message', str(response.status_code))
            except:
                error_msg = f'HTTP {response.status_code}'
            raise Exception(f'TTS API调用失败: {error_msg}')

def process_chat_task(task):
    """处理文生文任务"""
    api_key = task['api_key']
    prompt = task['prompt']
    
    content = call_chatglm_api(api_key, prompt)
    return {'content': content}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 语音克隆与生成教育智能体 - 本地服务</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1000px;
            margin: 20px auto;
            padding: 0 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .step-indicator {
            display: flex;
            gap: 20px;
        }
        .step {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 25px;
            background: #f5f5f5;
            transition: all 0.3s;
        }
        .step.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .step.disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .step-number {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: #ddd;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }
        .step.active .step-number {
            background: rgba(255,255,255,0.3);
        }
        .api-status {
            padding: 8px 16px;
            border-radius: 5px;
            font-size: 13px;
        }
        .api-status.connected {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .api-status.disconnected {
            background: #fff3e0;
            color: #e65100;
        }
        .section {
            margin-bottom: 30px;
            display: none;
        }
        .section.active {
            display: block;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 600;
            font-size: 14px;
        }
        input[type="text"], input[type="search"], textarea, select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus, input[type="search"]:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            resize: vertical;
            min-height: 120px;
            font-family: inherit;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        button.secondary {
            background: #f0f0f0;
            color: #666;
        }
        button.secondary:hover:not(:disabled) {
            background: #e0e0e0;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .audio-player {
            margin-top: 15px;
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
        }
        .message {
            margin-top: 12px;
            padding: 12px 15px;
            border-radius: 8px;
            display: none;
            font-size: 14px;
        }
        .message.error {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ef5350;
            display: block;
        }
        .message.success {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #66bb6a;
            display: block;
        }
        .message.info {
            background: #e3f2fd;
            color: #1565c0;
            border: 1px solid #42a5f5;
            display: block;
        }
        .tip {
            color: #888;
            font-size: 13px;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .mode-switch {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .mode-btn {
            padding: 10px 20px;
            background: #f0f0f0;
            border: 2px solid transparent;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        .mode-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
        }
        .voice-list-container {
            margin-top: 15px;
        }
        .voice-list-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .voice-search {
            width: 250px;
        }
        .voice-list {
            max-height: 300px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 10px;
        }
        .voice-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            background: #fafafa;
            cursor: pointer;
            transition: all 0.2s;
        }
        .voice-item:hover {
            background: #f0f0f0;
        }
        .voice-item.selected {
            background: #e3f2fd;
            border: 1px solid #42a5f5;
        }
        .voice-info {
            flex: 1;
        }
        .voice-name {
            font-weight: 600;
            color: #333;
        }
        .voice-id {
            font-family: monospace;
            font-size: 12px;
            color: #888;
            margin-top: 4px;
        }
        .voice-actions {
            display: flex;
            gap: 8px;
        }
        .action-btn {
            width: 32px;
            height: 32px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            transition: all 0.2s;
        }
        .action-btn.copy {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .action-btn.edit {
            background: #fff3e0;
            color: #e65100;
        }
        .action-btn.delete {
            background: #ffebee;
            color: #c62828;
        }
        .action-btn:hover {
            transform: scale(1.1);
        }
        .pagination {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
        }
        .page-btn {
            padding: 8px 16px;
            border: 1px solid #ddd;
            border-radius: 5px;
            cursor: pointer;
            background: white;
        }
        .page-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: #e0e0e0;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 15px;
            display: none;
        }
        .progress-bar.show {
            display: block;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s;
        }
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-overlay.show {
            display: flex;
        }
        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            min-width: 450px;
            max-width: 90%;
            max-height: 80%;
            overflow-y: auto;
        }
        .modal-content h3 {
            margin-top: 0;
            margin-bottom: 20px;
            color: #333;
            font-size: 20px;
        }
        .modal-close {
            float: right;
            cursor: pointer;
            font-size: 24px;
            color: #999;
            line-height: 1;
        }
        .modal-close:hover {
            color: #333;
        }
        .voice-id-display {
            font-family: monospace;
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            word-break: break-all;
            font-size: 14px;
            margin: 15px 0;
        }
        .file-upload-area {
            border: 2px dashed #ddd;
            border-radius: 10px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .file-upload-area:hover, .file-upload-area.dragover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .file-upload-area i {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 10px;
        }
        .file-info {
            margin-top: 10px;
            font-size: 13px;
            color: #888;
        }
        .hidden {
            display: none;
        }
        .flow-nav {
            display: flex;
            justify-content: space-between;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .nav-btn {
            padding: 10px 25px;
        }
        .disabled-section {
            opacity: 0.6;
            pointer-events: none;
        }
        .char-counter {
            text-align: right;
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 AI 语音克隆与生成教育智能体 - 本地服务</h1>
        
        <div class="step-header">
            <div class="step-indicator">
                <div class="step active" id="step1" onclick="goToStep(1)">
                    <span class="step-number">1</span>
                    <span>文生文</span>
                </div>
                <div class="step disabled" id="step2" onclick="goToStep(2)">
                    <span class="step-number">2</span>
                    <span>语音克隆</span>
                </div>
                <div class="step disabled" id="step3" onclick="goToStep(3)">
                    <span class="step-number">3</span>
                    <span>语音合成</span>
                </div>
            </div>
            <div id="apiStatus" class="api-status disconnected">API Key: 未配置</div>
        </div>

        <!-- 步骤1: 文生文 -->
        <div class="section active" id="section1">
            <h2>📝 文生文 - 生成配音文本</h2>
            
            <div class="mode-switch">
                <button class="mode-btn active" id="modeAi" onclick="setChatMode('ai')">AI生成（需API Key）</button>
                <button class="mode-btn" id="modeManual" onclick="setChatMode('manual')">手动输入</button>
            </div>
            
            <div class="form-group" id="promptGroup">
                <label for="prompt">输入生成指令</label>
                <textarea id="prompt" placeholder="例如：帮我写一段介绍人工智能的配音文案，要求简洁明了，适合语音播报。"></textarea>
                <div class="char-counter">0/2000</div>
            </div>
            
            <div class="form-group">
                <label for="generatedText">生成的文本（可编辑）</label>
                <textarea id="generatedText" placeholder="生成的文本将显示在这里，您可以进行编辑修改。"></textarea>
                <div class="char-counter">0/5000</div>
            </div>
            
            <div class="flow-nav">
                <div></div>
                <button class="nav-btn" onclick="generateText()" id="chatBtn">
                    <span id="chatBtnIcon">✨</span>
                    <span>生成文本</span>
                </button>
            </div>
            
            <div id="chatMessage" class="message"></div>
            <div class="progress-bar" id="chatProgress">
                <div class="progress-fill"></div>
            </div>
        </div>

        <!-- 步骤2: 语音克隆 -->
        <div class="section" id="section2">
            <h2>🎙️ 语音克隆 - 创建专属音色</h2>
            
            <div id="cloneDisabled" class="disabled-section">
                <div class="form-group">
                    <label for="cloneAudio">上传参考音频</label>
                    <div class="file-upload-area" id="uploadArea" onclick="document.getElementById('cloneAudioInput').click()">
                        <i>📁</i>
                        <p>点击或拖拽上传音频文件</p>
                        <p class="file-info">支持格式：wav, mp3, m4a, ogg, flac | 建议时长：10-60秒</p>
                    </div>
                    <input type="file" id="cloneAudioInput" class="hidden" accept=".wav,.mp3,.m4a,.ogg,.flac">
                    <div id="uploadedFileName" class="file-info"></div>
                </div>
                
                <div class="form-group">
                    <label for="cloneText">输入生成文本</label>
                    <textarea id="cloneText" placeholder="请输入要生成的文本内容，用于预览克隆效果"></textarea>
                    <div class="char-counter">0/500</div>
                </div>
                
                <div class="form-group">
                    <label for="sampleText">参考音频对应文本（选填）</label>
                    <textarea id="sampleText" placeholder="请输入参考音频对应的文本内容，有助于提高克隆质量"></textarea>
                    <p class="tip">📌 填写此内容可帮助系统更好地学习您的语音特征</p>
                </div>
                
                <div class="flow-nav">
                    <button class="nav-btn secondary" onclick="goToStep(1)">← 返回上一步</button>
                    <button class="nav-btn" onclick="startClone()" id="cloneBtn">
                        <span id="cloneBtnIcon">🎤</span>
                        <span>开始克隆</span>
                    </button>
                </div>
                
                <audio id="clonePlayer" class="audio-player" controls style="display:none;">
                <div id="cloneMessage" class="message"></div>
                <div class="progress-bar" id="cloneProgress">
                    <div class="progress-fill"></div>
                </div>
            </div>
            
            <div id="noApiKeyClone" style="display:none; padding: 30px; text-align: center; background: #fff3e0; border-radius: 10px;">
                <p style="font-size: 16px; color: #e65100; margin-bottom: 10px;">🔒 语音克隆功能需要配置API Key</p>
                <p style="font-size: 14px; color: #888;">请先在API Key配置中输入您的智谱API Key</p>
            </div>
        </div>

        <!-- 步骤3: 语音合成 -->
        <div class="section" id="section3">
            <h2>🔊 语音合成 - 生成音频</h2>
            
            <div class="mode-switch">
                <button class="mode-btn active" id="ttsModeApi" onclick="setTtsMode('api')">智谱TTS（需API Key）</button>
                <button class="mode-btn" id="ttsModeSystem" onclick="setTtsMode('system')">系统语音</button>
            </div>
            
            <div class="form-group">
                <label for="ttsText">合成文本</label>
                <textarea id="ttsText" placeholder="将从第一步获取的文本显示在这里"></textarea>
                <div class="char-counter">0/5000</div>
            </div>
            
            <div class="form-group" id="voiceSelectGroup">
                <label>选择音色</label>
                <div class="voice-list-container">
                    <div class="voice-list-header">
                        <input type="search" id="voiceSearch" class="voice-search" placeholder="搜索音色...">
                        <select id="voiceSort" style="padding: 8px 12px; border-radius: 5px;">
                            <option value="created_at_desc">按时间降序</option>
                            <option value="created_at_asc">按时间升序</option>
                            <option value="name_asc">按名称升序</option>
                            <option value="usage_desc">按使用次数</option>
                        </select>
                    </div>
                    <div id="voiceList" class="voice-list"></div>
                    <div class="pagination" id="voicePagination"></div>
                </div>
            </div>
            
            <div class="form-group" id="systemVoiceSelectGroup" style="display:none;">
                <label for="systemVoiceSelect">选择系统音色</label>
                <select id="systemVoiceSelect">
                    {% for voice in system_voices %}
                    <option value="{{ voice }}">{{ voice }}</option>
                    {% endfor %}
                </select>
            </div>
            
            <div class="flow-nav">
                <button class="nav-btn secondary" onclick="goToStep(2)">← 返回上一步</button>
                <button class="nav-btn" onclick="generateAudio()" id="ttsBtn">
                    <span id="ttsBtnIcon">🎧</span>
                    <span>生成音频</span>
                </button>
            </div>
            
            <audio id="ttsPlayer" class="audio-player" controls style="display:none;">
            <div id="ttsMessage" class="message"></div>
            <div class="progress-bar" id="ttsProgress">
                <div class="progress-fill"></div>
            </div>
        </div>
    </div>

    <!-- 音色ID显示弹窗 -->
    <div id="voiceIdModal" class="modal-overlay">
        <div class="modal-content">
            <span class="modal-close" onclick="closeModal()">&times;</span>
            <h3>🎉 音色复刻成功！</h3>
            <p>您的音色ID已生成，请妥善保存：</p>
            <div class="voice-id-display" id="newVoiceId"></div>
            <div class="form-group">
                <label for="newVoiceName">音色名称（可选）</label>
                <input type="text" id="newVoiceName" placeholder="为这个音色命名">
            </div>
            <div class="form-group">
                <label for="newVoiceRemark">备注（可选）</label>
                <input type="text" id="newVoiceRemark" placeholder="添加备注信息">
            </div>
            <button onclick="saveNewVoice()" style="width: 100%;">保存音色</button>
        </div>
    </div>

    <!-- 编辑音色弹窗 -->
    <div id="editVoiceModal" class="modal-overlay">
        <div class="modal-content">
            <span class="modal-close" onclick="closeEditModal()">&times;</span>
            <h3>编辑音色信息</h3>
            <div class="form-group">
                <label for="editVoiceName">音色名称</label>
                <input type="text" id="editVoiceName">
            </div>
            <div class="form-group">
                <label for="editVoiceRemark">备注</label>
                <input type="text" id="editVoiceRemark">
            </div>
            <div class="form-group">
                <label>音色ID（只读）</label>
                <div class="voice-id-display" id="editVoiceId"></div>
            </div>
            <button onclick="saveVoiceEdit()" style="width: 100%;">保存修改</button>
        </div>
    </div>

    <script>
        let currentStep = 1;
        let currentChatMode = 'ai';
        let currentTtsMode = 'api';
        let selectedVoiceId = '';
        let currentVoicePage = 1;
        let editingVoiceId = '';
        let pendingVoiceId = '';

        function checkApiKey() {
            const apiKey = localStorage.getItem('zhipuApiKey') || '';
            const statusEl = document.getElementById('apiStatus');
            const cloneSection = document.getElementById('cloneDisabled');
            const noApiKeyClone = document.getElementById('noApiKeyClone');
            
            if (apiKey) {
                statusEl.className = 'api-status connected';
                statusEl.textContent = 'API Key: 已配置';
                cloneSection.style.display = 'block';
                noApiKeyClone.style.display = 'none';
                return true;
            } else {
                statusEl.className = 'api-status disconnected';
                statusEl.textContent = 'API Key: 未配置';
                cloneSection.style.display = 'none';
                noApiKeyClone.style.display = 'block';
                return false;
            }
        }

        function goToStep(step) {
            if (step < currentStep) {
                currentStep = step;
                updateSteps();
            } else if (step === currentStep + 1) {
                if (currentStep === 1 && document.getElementById('generatedText').value.trim()) {
                    currentStep = step;
                    updateSteps();
                } else if (currentStep === 2) {
                    currentStep = step;
                    updateSteps();
                    loadVoices();
                }
            }
        }

        function updateSteps() {
            document.querySelectorAll('.section').forEach((el, index) => {
                el.classList.toggle('active', index + 1 === currentStep);
            });
            
            document.querySelectorAll('.step').forEach((el, index) => {
                el.classList.toggle('active', index + 1 === currentStep);
                el.classList.toggle('disabled', index + 1 > currentStep);
            });
            
            if (currentStep === 3) {
                document.getElementById('ttsText').value = document.getElementById('generatedText').value;
            }
        }

        function setChatMode(mode) {
            currentChatMode = mode;
            document.getElementById('modeAi').classList.toggle('active', mode === 'ai');
            document.getElementById('modeManual').classList.toggle('active', mode === 'manual');
            document.getElementById('promptGroup').style.display = mode === 'ai' ? 'block' : 'none';
        }

        function setTtsMode(mode) {
            currentTtsMode = mode;
            document.getElementById('ttsModeApi').classList.toggle('active', mode === 'api');
            document.getElementById('ttsModeSystem').classList.toggle('active', mode === 'system');
            document.getElementById('voiceSelectGroup').style.display = mode === 'api' ? 'block' : 'none';
            document.getElementById('systemVoiceSelectGroup').style.display = mode === 'system' ? 'block' : 'none';
            
            if (mode === 'system') {
                selectedVoiceId = document.getElementById('systemVoiceSelect').value;
            }
        }

        function showMessage(elementId, type, text) {
            const el = document.getElementById(elementId);
            el.className = 'message ' + type;
            el.textContent = text;
        }

        function hideMessage(elementId) {
            const el = document.getElementById(elementId);
            el.className = 'message';
        }

        function showProgress(progressId) {
            const bar = document.getElementById(progressId);
            bar.classList.add('show');
            bar.querySelector('.progress-fill').style.width = '30%';
        }

        function updateProgress(progressId, percent) {
            const bar = document.getElementById(progressId);
            bar.querySelector('.progress-fill').style.width = percent + '%';
        }

        function hideProgress(progressId) {
            const bar = document.getElementById(progressId);
            bar.classList.remove('show');
            bar.querySelector('.progress-fill').style.width = '0%';
        }

        async function generateText() {
            const generatedTextEl = document.getElementById('generatedText');
            
            if (currentChatMode === 'ai') {
                const prompt = document.getElementById('prompt').value.trim();
                
                if (!prompt) {
                    showMessage('chatMessage', 'error', '请输入生成指令');
                    return;
                }
                
                if (!checkApiKey()) {
                    showMessage('chatMessage', 'error', 'AI生成模式需要配置API Key');
                    return;
                }
                
                showProgress('chatProgress');
                showMessage('chatMessage', 'info', '正在生成文本...');
                
                const taskId = await createTask('chat', {
                    api_key: localStorage.getItem('zhipuApiKey'),
                    prompt: prompt
                });
                
                await pollTask(taskId, (result) => {
                    hideProgress('chatProgress');
                    if (result.status === 'completed') {
                        generatedTextEl.value = result.content;
                        showMessage('chatMessage', 'success', '文本生成成功！');
                    } else {
                        showMessage('chatMessage', 'error', '生成失败：' + result.error);
                    }
                });
            } else {
                if (!generatedTextEl.value.trim()) {
                    showMessage('chatMessage', 'error', '请输入文本内容');
                    return;
                }
                showMessage('chatMessage', 'success', '文本已准备好，可以进入下一步');
            }
        }

        async function startClone() {
            const audioFile = document.getElementById('cloneAudioInput').files[0];
            const text = document.getElementById('cloneText').value.trim();
            
            if (!audioFile) {
                showMessage('cloneMessage', 'error', '请上传参考音频');
                return;
            }
            
            if (!text) {
                showMessage('cloneMessage', 'error', '请输入生成文本');
                return;
            }
            
            if (!checkApiKey()) {
                showMessage('cloneMessage', 'error', '请先配置API Key');
                return;
            }
            
            showProgress('cloneProgress');
            showMessage('cloneMessage', 'info', '正在处理...这可能需要1-2分钟');
            
            const formData = new FormData();
            formData.append('audio', audioFile);
            formData.append('text', text);
            formData.append('sample_text', document.getElementById('sampleText').value);
            formData.append('api_key', localStorage.getItem('zhipuApiKey'));
            
            const response = await fetch('/api/clone/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
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
            } else {
                hideProgress('cloneProgress');
                showMessage('cloneMessage', 'error', result.error);
            }
        }

        async function generateAudio() {
            const text = document.getElementById('ttsText').value.trim();
            
            if (!text) {
                showMessage('ttsMessage', 'error', '请输入要合成的文本');
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

        async function createTask(taskType, data) {
            const response = await fetch('/api/task/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: taskType, data: data })
            });
            const result = await response.json();
            return result.task_id;
        }

        async function pollTask(taskId, callback) {
            const interval = setInterval(async () => {
                const response = await fetch(`/api/task/status/${taskId}`);
                const result = await response.json();
                
                if (result.status === 'completed' || result.status === 'error') {
                    clearInterval(interval);
                    callback(result);
                }
            }, 1000);
        }

        function saveNewVoice() {
            const name = document.getElementById('newVoiceName').value.trim();
            const remark = document.getElementById('newVoiceRemark').value.trim();
            
            fetch('/api/voices/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    voice_id: pendingVoiceId,
                    name: name,
                    remark: remark
                })
            }).then(() => {
                closeModal();
                loadVoices();
            });
        }

        function closeModal() {
            document.getElementById('voiceIdModal').classList.remove('show');
            pendingVoiceId = '';
        }

        async function loadVoices(page = 1) {
            const search = document.getElementById('voiceSearch').value;
            const sort = document.getElementById('voiceSort').value;
            const [sortBy, sortOrder] = sort.split('_');
            
            const response = await fetch(`/api/voices?search=${encodeURIComponent(search)}&page=${page}&sort_by=${sortBy}&sort_order=${sortOrder}`);
            const result = await response.json();
            
            if (result.success) {
                const list = document.getElementById('voiceList');
                if (result.data.voices.length > 0) {
                    list.innerHTML = result.data.voices.map(item => `
                        <div class="voice-item ${selectedVoiceId === item.voice_id ? 'selected' : ''}" onclick="selectVoice('${item.voice_id}')">
                            <div class="voice-info">
                                <div class="voice-name">${item.name || '未命名音色'}</div>
                                <div class="voice-id">${item.voice_id}</div>
                                ${item.remark ? `<div style="font-size:12px;color:#666;margin-top:4px;">${item.remark}</div>` : ''}
                            </div>
                            <div class="voice-actions">
                                <button class="action-btn copy" onclick="copyVoiceId('${item.voice_id}', event)" title="复制">📋</button>
                                <button class="action-btn edit" onclick="openEditModal('${item.voice_id}', '${item.name || ''}', '${item.remark || ''}')" title="编辑">✏️</button>
                                <button class="action-btn delete" onclick="deleteVoice('${item.voice_id}', event)" title="删除">🗑️</button>
                            </div>
                        </div>
                    `).join('');
                    
                    renderPagination(result.data);
                } else {
                    list.innerHTML = '<p style="text-align:center;color:#888;padding:20px;">暂无音色</p>';
                    document.getElementById('voicePagination').innerHTML = '';
                }
            }
        }

        function renderPagination(data) {
            const pagination = document.getElementById('voicePagination');
            const totalPages = data.total_pages;
            const currentPage = data.page;
            
            let html = '';
            if (currentPage > 1) {
                html += `<button class="page-btn" onclick="loadVoices(${currentPage - 1})">上一页</button>`;
            }
            
            for (let i = 1; i <= totalPages; i++) {
                html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="loadVoices(${i})">${i}</button>`;
            }
            
            if (currentPage < totalPages) {
                html += `<button class="page-btn" onclick="loadVoices(${currentPage + 1})">下一页</button>`;
            }
            
            pagination.innerHTML = html;
        }

        function selectVoice(voiceId) {
            selectedVoiceId = voiceId;
            document.querySelectorAll('.voice-item').forEach(el => {
                el.classList.remove('selected');
            });
            document.querySelector(`.voice-item[onclick="selectVoice('${voiceId}')"]`).classList.add('selected');
        }

        async function copyVoiceId(voiceId, event) {
            event.stopPropagation();
            try {
                await navigator.clipboard.writeText(voiceId);
                alert('音色ID已复制到剪贴板');
            } catch (e) {
                alert('复制失败，请手动复制');
            }
        }

        function openEditModal(voiceId, name, remark) {
            editingVoiceId = voiceId;
            document.getElementById('editVoiceName').value = name;
            document.getElementById('editVoiceRemark').value = remark;
            document.getElementById('editVoiceId').textContent = voiceId;
            document.getElementById('editVoiceModal').classList.add('show');
        }

        function closeEditModal() {
            document.getElementById('editVoiceModal').classList.remove('show');
            editingVoiceId = '';
        }

        async function saveVoiceEdit() {
            const name = document.getElementById('editVoiceName').value;
            const remark = document.getElementById('editVoiceRemark').value;
            
            await fetch('/api/voices/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    voice_id: editingVoiceId,
                    name: name,
                    remark: remark
                })
            });
            
            closeEditModal();
            loadVoices(currentVoicePage);
        }

        async function deleteVoice(voiceId, event) {
            event.stopPropagation();
            if (!confirm('确定要删除这个音色吗？')) {
                return;
            }
            
            await fetch('/api/voices/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ voice_id: voiceId })
            });
            
            if (selectedVoiceId === voiceId) {
                selectedVoiceId = '';
            }
            loadVoices(currentVoicePage);
        }

        document.getElementById('apiStatus').addEventListener('click', () => {
            const apiKey = prompt('请输入您的智谱API Key：', localStorage.getItem('zhipuApiKey') || '');
            if (apiKey !== null) {
                localStorage.setItem('zhipuApiKey', apiKey);
                checkApiKey();
            }
        });

        document.getElementById('uploadArea').addEventListener('dragover', (e) => {
            e.preventDefault();
            document.getElementById('uploadArea').classList.add('dragover');
        });

        document.getElementById('uploadArea').addEventListener('dragleave', () => {
            document.getElementById('uploadArea').classList.remove('dragover');
        });

        document.getElementById('uploadArea').addEventListener('drop', (e) => {
            e.preventDefault();
            document.getElementById('uploadArea').classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                document.getElementById('cloneAudioInput').files = files;
                document.getElementById('uploadedFileName').textContent = '已选择: ' + files[0].name;
            }
        });

        document.getElementById('cloneAudioInput').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                document.getElementById('uploadedFileName').textContent = '已选择: ' + e.target.files[0].name;
            }
        });

        document.getElementById('voiceSearch').addEventListener('input', () => {
            loadVoices(1);
        });

        document.getElementById('voiceSort').addEventListener('change', () => {
            loadVoices(1);
        });

        document.getElementById('prompt').addEventListener('input', (e) => {
            e.target.nextElementSibling.textContent = e.target.value.length + '/2000';
        });

        document.getElementById('generatedText').addEventListener('input', (e) => {
            e.target.nextElementSibling.textContent = e.target.value.length + '/5000';
        });

        document.getElementById('cloneText').addEventListener('input', (e) => {
            e.target.nextElementSibling.textContent = e.target.value.length + '/500';
        });

        document.getElementById('ttsText').addEventListener('input', (e) => {
            e.target.nextElementSibling.textContent = e.target.value.length + '/5000';
        });

        document.getElementById('systemVoiceSelect').addEventListener('change', (e) => {
            selectedVoiceId = e.target.value;
        });

        checkApiKey();
    </script>
</body>
</html>
"""

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, system_voices=SYSTEM_VOICES)

@app.route('/api/outputs/<filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/api/task/create', methods=['POST'])
def create_task():
    data = request.get_json()
    task_type = data.get('type')
    task_data = data.get('data')
    
    task_id = str(uuid.uuid4())
    task_results[task_id] = {'status': 'running'}
    
    task_queue.put({
        'task_id': task_id,
        'task_type': task_type,
        **task_data
    })
    
    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/task/status/<task_id>')
def get_task_status(task_id):
    result = task_results.get(task_id, {'status': 'not_found'})
    return jsonify(result)

@app.route('/api/clone/upload', methods=['POST'])
def clone_upload():
    try:
        api_key = request.form.get('api_key')
        text = request.form.get('text')
        sample_text = request.form.get('sample_text', '')
        audio_file = request.files.get('audio')
        
        if not api_key or not text or not audio_file:
            return jsonify({'success': False, 'error': '参数不完整'})
        
        temp_audio_path = os.path.join(OUTPUT_DIR, f'temp_{int(time.time())}_{audio_file.filename}')
        audio_file.save(temp_audio_path)
        
        task_id = str(uuid.uuid4())
        task_results[task_id] = {'status': 'running'}
        
        task_queue.put({
            'task_id': task_id,
            'task_type': 'clone',
            'api_key': api_key,
            'audio_path': temp_audio_path,
            'text': text,
            'sample_text': sample_text
        })
        
        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/voices', methods=['GET'])
def get_voices():
    try:
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        result = get_voices_from_db(search, page, per_page, sort_by, sort_order)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/voices/save', methods=['POST'])
def save_voice():
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        name = data.get('name', '')
        remark = data.get('remark', '')
        
        save_voice_to_db(voice_id, name, remark)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/voices/update', methods=['POST'])
def update_voice():
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        name = data.get('name', '')
        remark = data.get('remark', '')
        
        if name:
            update_voice_name(voice_id, name)
        if remark:
            update_voice_remark(voice_id, remark)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/voices/delete', methods=['POST'])
def delete_voice():
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        
        delete_voice_from_db(voice_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def kill_port(port):
    """清理指定端口的占用进程"""
    try:
        if sys.platform == 'win32':
            # Windows平台
            subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            result = subprocess.run(
                ['powershell', '-Command', f'Get-NetTCPConnection -LocalPort {port} | Select-Object -ExpandProperty OwningProcess'],
                capture_output=True, text=True
            )
            pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip().isdigit()]
            for pid in pids:
                try:
                    subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                    print(f'⚡ 已终止占用端口 {port} 的进程: {pid}')
                except:
                    pass
        else:
            # Mac/Linux平台
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    try:
                        subprocess.run(['kill', '-9', pid.strip()], capture_output=True)
                        print(f'⚡ 已终止占用端口 {port} 的进程: {pid.strip()}')
                    except:
                        pass
    except Exception as e:
        print(f'⚠️ 清理端口时发生错误: {e}')

def open_browser(port=7860):
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{port}')

if __name__ == '__main__':
    port = 7860
    
    # 清理端口占用
    print(f'⚡ 检查并清理端口 {port}...')
    kill_port(port)
    
    init_db()
    
    worker_thread = threading.Thread(target=async_task_worker)
    worker_thread.daemon = True
    worker_thread.start()
    
    print('='*60)
    print('🚀 智谱AI 语音克隆 Web 服务启动中...')
    print('='*60)
    print(f'📂 输出目录: {OUTPUT_DIR}')
    print(f'🗄️ 数据库: {DB_PATH}')
    print(f'🌐 访问地址: http://localhost:{port}')
    print('='*60)
    
    browser_thread = threading.Thread(target=open_browser, args=(port,))
    browser_thread.daemon = True
    browser_thread.start()
    
    app.run(host='0.0.0.0', port=port, debug=False)
