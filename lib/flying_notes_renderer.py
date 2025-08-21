import time
import json
import threading
from collections import deque
from lib.log_setup import logger


class FlyingNotesRenderer:
    """Handles the flying notes visualization system"""
    
    def __init__(self, usersettings, learnmidi):
        self.usersettings = usersettings
        self.learnmidi = learnmidi
        self.websocket_clients = set()
        self.is_active = False
        self.animation_thread = None
        self.notes_buffer = deque(maxlen=1000)  # Store upcoming notes
        self.current_time = 0
        self.start_time = 0
        
        # Piano keyboard layout (88 keys)
        self.piano_keys = self._generate_piano_layout()
        
        # Animation settings
        self.settings = {
            'enabled': False,
            'speed': 1.0,
            'note_height': 20,
            'keyboard_height': 80,
            'show_measures': True,
            'animation_smoothness': 60,
            'canvas_height': 600,
            'fall_distance': 520  # Distance notes travel before reaching keyboard
        }
        
        self._load_settings()
    
    def _generate_piano_layout(self):
        """Generate piano keyboard layout with key positions"""
        keys = []
        white_key_width = 20
        black_key_width = 12
        white_key_count = 0
        
        # Standard 88-key piano: A0 (21) to C8 (108)
        for midi_note in range(21, 109):
            note_in_octave = midi_note % 12
            is_black = note_in_octave in [1, 3, 6, 8, 10]  # C#, D#, F#, G#, A#
            
            if not is_black:
                x_position = white_key_count * white_key_width
                white_key_count += 1
            else:
                # Position black keys between white keys
                black_key_offset = {
                    1: -6,   # C#
                    3: 6,    # D#
                    6: -8,   # F#
                    8: 0,    # G#
                    10: 8    # A#
                }[note_in_octave]
                x_position = (white_key_count - 1) * white_key_width + white_key_width // 2 + black_key_offset
            
            keys.append({
                'midi_note': midi_note,
                'x_position': x_position,
                'is_black': is_black,
                'width': black_key_width if is_black else white_key_width
            })
        
        return keys
    
    def _load_settings(self):
        """Load flying notes settings from user configuration"""
        try:
            self.settings['enabled'] = bool(int(self.usersettings.get_setting_value("flying_notes/enabled")))
            self.settings['speed'] = float(self.usersettings.get_setting_value("flying_notes/speed"))
            self.settings['note_height'] = int(self.usersettings.get_setting_value("flying_notes/note_height"))
            self.settings['keyboard_height'] = int(self.usersettings.get_setting_value("flying_notes/keyboard_height"))
            self.settings['show_measures'] = bool(int(self.usersettings.get_setting_value("flying_notes/show_measures")))
            self.settings['animation_smoothness'] = int(self.usersettings.get_setting_value("flying_notes/animation_smoothness"))
        except Exception as e:
            logger.warning(f"Failed to load flying notes settings: {e}")
    
    def add_websocket_client(self, client):
        """Add a WebSocket client for real-time updates"""
        self.websocket_clients.add(client)
    
    def remove_websocket_client(self, client):
        """Remove a WebSocket client"""
        self.websocket_clients.discard(client)
    
    def start_animation(self):
        """Start the flying notes animation"""
        if self.is_active or not self.settings['enabled']:
            return
        
        self.is_active = True
        self.start_time = time.time()
        self.current_time = 0
        
        # Load notes from current MIDI song
        self._load_notes_from_midi()
        
        # Start animation thread
        self.animation_thread = threading.Thread(target=self._animation_loop)
        self.animation_thread.daemon = True
        self.animation_thread.start()
        
        logger.info("Flying notes animation started")
    
    def stop_animation(self):
        """Stop the flying notes animation"""
        self.is_active = False
        if self.animation_thread:
            self.animation_thread.join(timeout=1.0)
        
        # Clear notes buffer
        self.notes_buffer.clear()
        
        # Send stop signal to clients
        self._broadcast_to_clients({'type': 'stop'})
        
        logger.info("Flying notes animation stopped")
    
    def _load_notes_from_midi(self):
        """Load notes from the current MIDI song"""
        if not hasattr(self.learnmidi, 'song_tracks') or not self.learnmidi.song_tracks:
            return
        
        self.notes_buffer.clear()
        current_time = 0
        
        for msg in self.learnmidi.song_tracks:
            if not msg.is_meta:
                current_time += msg.time
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    # Convert MIDI ticks to seconds
                    time_seconds = current_time * self.learnmidi.song_tempo / (self.learnmidi.ticks_per_beat * 1000000)
                    
                    note_data = {
                        'midi_note': msg.note,
                        'channel': msg.channel,
                        'velocity': msg.velocity,
                        'start_time': time_seconds,
                        'duration': 1.0,  # Default duration, will be updated by note_off
                        'hand': 'right' if msg.channel == 1 else 'left',
                        'note_type': self.learnmidi.get_note_type(msg.note)
                    }
                    
                    self.notes_buffer.append(note_data)
        
        logger.info(f"Loaded {len(self.notes_buffer)} notes for flying notes animation")
    
    def _animation_loop(self):
        """Main animation loop"""
        frame_time = 1.0 / self.settings['animation_smoothness']
        
        while self.is_active:
            start_frame_time = time.time()
            
            # Update current time
            self.current_time = (time.time() - self.start_time) * self.settings['speed']
            
            # Generate frame data
            frame_data = self._generate_frame_data()
            
            # Broadcast to WebSocket clients
            self._broadcast_to_clients({
                'type': 'frame_update',
                'data': frame_data,
                'current_time': self.current_time
            })
            
            # Sleep to maintain frame rate
            elapsed = time.time() - start_frame_time
            sleep_time = max(0, frame_time - elapsed)
            time.sleep(sleep_time)
    
    def _generate_frame_data(self):
        """Generate frame data for the current time"""
        visible_notes = []
        lookahead_time = self.settings['fall_distance'] / 100.0  # Time for notes to fall
        
        for note in self.notes_buffer:
            note_start_time = note['start_time']
            
            # Check if note should be visible
            if (self.current_time <= note_start_time <= self.current_time + lookahead_time):
                # Calculate note position
                time_until_hit = note_start_time - self.current_time
                y_position = self.settings['canvas_height'] - self.settings['keyboard_height'] - (
                    time_until_hit / lookahead_time * self.settings['fall_distance']
                )
                
                # Get note color
                color = self.learnmidi.get_learn_color(
                    note['hand'], 
                    note['note_type'], 
                    is_upcoming=True
                )
                
                # Find piano key position
                key_info = next((k for k in self.piano_keys if k['midi_note'] == note['midi_note']), None)
                if key_info:
                    visible_notes.append({
                        'midi_note': note['midi_note'],
                        'x_position': key_info['x_position'],
                        'y_position': y_position,
                        'width': key_info['width'],
                        'height': self.settings['note_height'],
                        'color': color,
                        'hand': note['hand'],
                        'velocity': note['velocity'],
                        'is_black_key': key_info['is_black']
                    })
        
        return {
            'notes': visible_notes,
            'piano_keys': self.piano_keys,
            'settings': self.settings
        }
    
    def _broadcast_to_clients(self, data):
        """Broadcast data to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message = json.dumps(data)
        disconnected_clients = set()
        
        for client in self.websocket_clients:
            try:
                client.send(message)
            except Exception as e:
                logger.warning(f"Failed to send data to WebSocket client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.websocket_clients.discard(client)
    
    def update_settings(self, new_settings):
        """Update flying notes settings"""
        self.settings.update(new_settings)
        
        # Save to user settings
        for key, value in new_settings.items():
            if key in ['enabled', 'show_measures']:
                self.usersettings.change_setting_value(f"flying_notes/{key}", int(value))
            else:
                self.usersettings.change_setting_value(f"flying_notes/{key}", value)
        
        # Restart animation if active
        if self.is_active:
            self.stop_animation()
            if self.settings['enabled']:
                self.start_animation()
    
    def get_settings(self):
        """Get current flying notes settings"""
        return self.settings.copy()
    
    def sync_with_learn_midi(self, current_position):
        """Synchronize flying notes with learn MIDI position"""
        if self.is_active:
            # Update current time based on MIDI position
            self.current_time = current_position