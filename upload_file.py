import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- Configuration ---
# Get your API key from https://ocr.space/ocrapi
OCR_API_KEY = 'YOUR_OCR_SPACE_API_KEY'  # Replace with your actual API key
UPLOAD_FOLDER = 'uploads'  # Folder to temporarily store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB file size

# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # --- Send image to OCR.space ---
        try:
            with open(filepath, 'rb') as f:
                payload = {
                    'apikey': OCR_API_KEY,
                    'language': 'eng',  # You can change the language here (e.g., 'fre', 'spa')
                    'isOverlayRequired': False,  # Set to True if you want text overlay data
                    'OCREngine': 2 # Use OCR Engine 2 for better results
                }
                files = {'file': f}
                
                # Make the POST request to OCR.space API
                response = requests.post('https://api.ocr.space/parse/image',
                                         files=files,
                                         data=payload)
                response.raise_for_status()  # Raise an exception for HTTP errors

                result = response.json()

                # Process the OCR result
                if result['OCRExitCode'] == 1:  # Success
                    parsed_text = result['ParsedResults'][0]['ParsedText']
                    return jsonify({'success': True, 'text': parsed_text})
                elif result['OCRExitCode'] == 2: # Partial Success
                    parsed_text = result['ParsedResults'][0]['ParsedText']
                    error_message = result.get('ErrorMessage', 'Partial success, some errors occurred.')
                    return jsonify({'success': True, 'text': parsed_text, 'warning': error_message})
                else:
                    error_message = result.get('ErrorMessage', 'OCR failed with an unknown error.')
                    return jsonify({'success': False, 'error': error_message}), 500

        except requests.exceptions.RequestException as e:
            return jsonify({'success': False, 'error': f"Network error or API issue: {e}"}), 500
        except KeyError:
            return jsonify({'success': False, 'error': "Unexpected OCR.space API response format."}), 500
        finally:
            # Clean up the uploaded file after processing
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True)