from webinterface import webinterface, app_state
from flask import render_template, request, jsonify
import os
import time
import webcolors as wc
from lib.flying_notes_renderer import FlyingNotesRenderer
from lib.websocket_handler import WebSocketHandler, FlyingNotesWebSocketClient

# Global instances for flying notes functionality
flying_notes_renderer = None
websocket_handler = None

ALLOWED_EXTENSIONS = {'mid', 'musicxml', 'mxl', 'xml', 'abc'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@webinterface.before_request
def before_request():
    excluded_routes = ['/api/get_homepage_data']

    # Check if the current request path is in the excluded_routes list
    if request.path not in excluded_routes:
        app_state.menu.last_activity = time.time()
        app_state.menu.is_idle_animation_running = False


@webinterface.route('/')
def index():
    return render_template('index.html')


@webinterface.route('/home')
def home():
    return render_template('home.html')


@webinterface.route('/ledsettings')
def ledsettings():
    return render_template('ledsettings.html')


@webinterface.route('/ledanimations')
def ledanimations():
    return render_template('ledanimations.html')


@webinterface.route('/songs')
def songs():
    return render_template('songs.html')


@webinterface.route('/sequences')
def sequences():
    return render_template('sequences.html')


@webinterface.route('/ports')
def ports():
    return render_template('ports.html')


@webinterface.route('/network')
def network():
    return render_template('network.html')


@webinterface.route('/flying_notes')
def flying_notes():
    return render_template('flying_notes.html')


@webinterface.route('/usb_gadget')
def usb_gadget():
    return render_template('usb_gadget.html')


@webinterface.route('/api/flying_notes/start', methods=['POST'])
def start_flying_notes():
    """API endpoint to start flying notes animation"""
    try:
        if flying_notes_renderer:
            flying_notes_renderer.start_animation()
            return jsonify(success=True, message="Flying notes animation started")
        else:
            return jsonify(success=False, error="Flying notes renderer not initialized")
    except Exception as e:
        return jsonify(success=False, error=str(e))


@webinterface.route('/api/flying_notes/stop', methods=['POST'])
def stop_flying_notes():
    """API endpoint to stop flying notes animation"""
    try:
        if flying_notes_renderer:
            flying_notes_renderer.stop_animation()
            return jsonify(success=True, message="Flying notes animation stopped")
        else:
            return jsonify(success=False, error="Flying notes renderer not initialized")
    except Exception as e:
        return jsonify(success=False, error=str(e))


@webinterface.route('/api/flying_notes/settings', methods=['GET', 'POST'])
def flying_notes_settings():
    """API endpoint to get or update flying notes settings"""
    try:
        if not flying_notes_renderer:
            return jsonify(success=False, error="Flying notes renderer not initialized")
        
        if request.method == 'GET':
            settings = flying_notes_renderer.get_settings()
            return jsonify(success=True, settings=settings)
        
        elif request.method == 'POST':
            new_settings = request.get_json()
            flying_notes_renderer.update_settings(new_settings)
            return jsonify(success=True, message="Settings updated")
    
    except Exception as e:
        return jsonify(success=False, error=str(e))


@webinterface.route('/api/learn_colors/settings', methods=['GET', 'POST'])
def learn_colors_settings():
    """API endpoint to get or update enhanced learn color settings"""
    try:
        if request.method == 'GET':
            # Helper function to convert RGB array to hex color
            def rgb_array_to_hex(rgb_str):
                if rgb_str:
                    try:
                        import ast
                        rgb_array = ast.literal_eval(rgb_str)
                        if isinstance(rgb_array, list) and len(rgb_array) >= 3:
                            return wc.rgb_to_hex((rgb_array[0], rgb_array[1], rgb_array[2]))
                    except (ValueError, SyntaxError):
                        pass
                return '#FFFFFF'  # Default to white if invalid
            
            # Get current color settings from usersettings
            settings = {
                'left_hand': {
                    'white_current': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/left_hand/white_keys/current")),
                    'white_upcoming': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/left_hand/white_keys/upcoming")),
                    'black_current': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/left_hand/black_keys/current")),
                    'black_upcoming': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/left_hand/black_keys/upcoming"))
                },
                'right_hand': {
                    'white_current': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/right_hand/white_keys/current")),
                    'white_upcoming': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/right_hand/white_keys/upcoming")),
                    'black_current': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/right_hand/black_keys/current")),
                    'black_upcoming': rgb_array_to_hex(app_state.usersettings.get_setting_value("learn_colors/right_hand/black_keys/upcoming"))
                }
            }
            return jsonify(success=True, settings=settings)
        
        elif request.method == 'POST':
            new_settings = request.get_json()
            
            # Helper function to convert hex color to RGB array
            def hex_to_rgb_array(hex_color):
                if hex_color and hex_color.startswith('#'):
                    try:
                        rgb = wc.hex_to_rgb(hex_color)
                        return [rgb.red, rgb.green, rgb.blue]
                    except ValueError:
                        return [255, 255, 255]  # Default to white if invalid
                return [255, 255, 255]  # Default to white if no color
            
            # Helper function to create dimmed version of RGB array (30% brightness)
            def dim_rgb_array(rgb_array, brightness_factor=0.3):
                return [int(color * brightness_factor) for color in rgb_array]
            
            # Update color settings in usersettings
            for hand in ['left_hand', 'right_hand']:
                if hand in new_settings:
                    if 'white_current' in new_settings[hand]:
                        # Set current color
                        setting_path = f"learn_colors/{hand}/white_keys/current"
                        rgb_array = hex_to_rgb_array(new_settings[hand]['white_current'])
                        app_state.usersettings.change_setting_value(setting_path, str(rgb_array))
                        
                        # Automatically set dimmed upcoming color
                        upcoming_path = f"learn_colors/{hand}/white_keys/upcoming"
                        dimmed_rgb = dim_rgb_array(rgb_array)
                        app_state.usersettings.change_setting_value(upcoming_path, str(dimmed_rgb))
                    
                    if 'black_current' in new_settings[hand]:
                        # Set current color
                        setting_path = f"learn_colors/{hand}/black_keys/current"
                        rgb_array = hex_to_rgb_array(new_settings[hand]['black_current'])
                        app_state.usersettings.change_setting_value(setting_path, str(rgb_array))
                        
                        # Automatically set dimmed upcoming color
                        upcoming_path = f"learn_colors/{hand}/black_keys/upcoming"
                        dimmed_rgb = dim_rgb_array(rgb_array)
                        app_state.usersettings.change_setting_value(upcoming_path, str(dimmed_rgb))
            
            # Reload settings in LearnMIDI if available
            if hasattr(app_state, 'learning') and app_state.learning:
                app_state.learning.reload_enhanced_colors()
            
            return jsonify(success=True, message="Color settings updated")
    
    except Exception as e:
        return jsonify(success=False, error=str(e))


@webinterface.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify(success=False, error="no file")
        file = request.files['file']
        filename = file.filename
        if os.path.exists("Songs/" + filename):
            return jsonify(success=False, error="file already exists", song_name=filename)
        if not allowed_file(file.filename):
            return jsonify(success=False, error="not a midi file", song_name=filename)

        filename = filename.replace("'", "")
        file.save(os.path.join(webinterface.config['UPLOAD_FOLDER'], filename))
        return jsonify(success=True, reload_songs=True, song_name=filename)
