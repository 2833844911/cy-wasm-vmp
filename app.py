import os
import uuid
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from wasm_vmp import JiexStart

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB limit

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# In-memory job store
# Structure: { job_id: { 'status': 'processing'|'done'|'error', 'message': str, 'output_file': str } }
JOBS = {}

def process_wasm(job_id, input_path, output_path, selected_functions=None):
    """Background task to process the WASM file."""
    try:
        print(f"[{job_id}] Starting processing: {input_path} -> {output_path}")
        
        processor = JiexStart(input_path)
        processor.parse_module()
        processor.encrypt_module(output_path, not_jeb=True, selected_functions=selected_functions)
        
        JOBS[job_id]['status'] = 'done'
        JOBS[job_id]['output_file'] = output_path
        print(f"[{job_id}] Processing complete.")
    except Exception as e:
        print(f"[{job_id}] Error: {e}")
        JOBS[job_id]['status'] = 'error'
        JOBS[job_id]['message'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        job_id = str(uuid.uuid4())
        filename = f"{job_id}_{file.filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        output_filename = f"protected_{file.filename}"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        file.save(input_path)
        
        # Store job info but don't start processing yet
        JOBS[job_id] = {
            'status': 'uploaded',
            'input_path': input_path,
            'output_path': output_path,
            'filename': file.filename
        }
        
        return jsonify({'job_id': job_id})

@app.route('/analyze/<job_id>')
def analyze_wasm(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    try:
        processor = JiexStart(job['input_path'])
        processor.parse_module()
        
        funcs = []
        # Iterate over function_codes to get internal functions
        for i, func in enumerate(processor.function_codes):
            global_idx = processor.codec.imported_func_count + i
            name = func.get('name', '')
            lines = len(func['code'])
            funcs.append({
                'index': global_idx,
                'name': name,
                'lines': lines
            })
            
        return jsonify({'functions': funcs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/encrypt', methods=['POST'])
def start_encryption():
    data = request.json
    job_id = data.get('job_id')
    selected_functions = data.get('selected_functions') # List of integers
    
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    if job['status'] != 'uploaded':
        return jsonify({'error': 'Job already processed or invalid state'}), 400
        
    job['status'] = 'processing'
    
    # Start background thread
    thread = threading.Thread(target=process_wasm, args=(job_id, job['input_path'], job['output_path'], selected_functions))
    thread.start()
    
    return jsonify({'status': 'started'})

@app.route('/status/<job_id>')
def check_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    # Return a subset of job info to avoid leaking paths
    return jsonify({
        'status': job['status'],
        'message': job.get('message')
    })

@app.route('/download/<job_id>')
def download_file(job_id):
    job = JOBS.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': 'File not ready or job not found'}), 404
    
    return send_file(job['output_file'], as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=25100)
