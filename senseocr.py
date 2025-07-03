import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename # Still useful, but we'll override the filename

senseocr = Flask(__name__)

# --- Configuration ---
# Get your API key from https://ocr.space/ocrapi
OCR_API_KEY = 'K82220898388957'  # Replace with your actual API key
UPLOAD_FOLDER = 'uploads'  # Folder to temporarily store captured images
# We only care about PNG now as we're capturing as PNG
ALLOWED_EXTENSIONS = {'png'} # Changed to only allow PNG

senseocr.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
senseocr.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB file size

# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@senseocr.route('/GetText', methods=['GET'])
def GetText():
    #return redirect(url_for('upload_file'))
    return render_template('GetText.html')

@senseocr.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # We are now forcing the filename to default.png
    # No need to check file.filename == '' as it's always provided by JS
    # and no need for secure_filename here as we are dictating the name
    
    if file and allowed_file(file.filename): # Still check if it's a PNG from the client side
        # Force the filename to default.png
        filename = 'default.png'
        filepath = os.path.join(senseocr.config['UPLOAD_FOLDER'], filename)
        
        # Save the incoming photo to default.png, overwriting if it exists
        file.save(filepath)

        # --- Send image to OCR.space ---
        try:
            with open(filepath, 'rb') as f:
                payload = {
                    'apikey': OCR_API_KEY,
                    'language': 'eng',  # You can change the language here (e.g., 'fre', 'spa')
                    'isOverlayRequired': False,
                    'OCREngine': 2
                }
                files = {'file': f}
                
                response = requests.post('https://api.ocr.space/parse/image',
                                         files=files,
                                         data=payload)
                response.raise_for_status()

                result = response.json()

                if result['OCRExitCode'] == 1:
                    parsed_text = result['ParsedResults'][0]['ParsedText']
                    return jsonify({'success': True, 'text': parsed_text})
                elif result['OCRExitCode'] == 2:
                    parsed_text = result['ParsedResults'][0]['ParsedText']
                    error_message = result.get('ErrorMessage', 'Partial success, some errors occurred.')
                    return jsonify({'success': True, 'text': parsed_text, 'warning': error_message})
                else:
                    error_message = result.get('ErrorMessage', 'OCR failed with an unknown error.')
                    # Also include any detailed errors from OCR.space
                    if 'ErrorMessage' in result:
                        error_message += " Details: " + ", ".join(result['ErrorMessage'])
                    if 'ErrorDetails' in result:
                        error_message += " Error Details: " + result['ErrorDetails']
                    return jsonify({'success': False, 'error': error_message}), 500

        except requests.exceptions.RequestException as e:
            return jsonify({'success': False, 'error': f"Network error or API issue: {e}"}), 500
        except KeyError:
            return jsonify({'success': False, 'error': "Unexpected OCR.space API response format. Missing 'ParsedResults' or 'OCRExitCode'."}), 500
        finally:
            # Clean up the uploaded file after processing
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        # This case should ideally not be hit if client-side JS is correct
        #return render_template('GetText.html')
        return jsonify({'error': 'Invalid file type. Only PNG is supported for capture.'}), 400

if __name__ == '__main__':
    senseocr.run(debug=True)