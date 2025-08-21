import json
import threading
from flask import Flask
from flask_socketio import SocketIO, emit, disconnect
from lib.log_setup import logger


class WebSocketHandler:
    """Handles WebSocket communication for flying notes visualization"""
    
    def __init__(self, app, flying_notes_renderer):
        self.app = app
        self.flying_notes_renderer = flying_notes_renderer
        self.socketio = SocketIO(app, cors_allowed_origins="*")
        self.connected_clients = set()
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            client_id = id(self.socketio)
            self.connected_clients.add(client_id)
            logger.info(f"WebSocket client connected: {client_id}")
            
            # Send initial settings
            emit('settings_update', self.flying_notes_renderer.get_settings())
            
            # If animation is active, send current state
            if self.flying_notes_renderer.is_active:
                emit('animation_started')
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = id(self.socketio)
            self.connected_clients.discard(client_id)
            logger.info(f"WebSocket client disconnected: {client_id}")
        
        @self.socketio.on('start_animation')
        def handle_start_animation():
            """Handle start animation request"""
            try:
                self.flying_notes_renderer.start_animation()
                self.socketio.emit('animation_started', broadcast=True)
                logger.info("Flying notes animation started via WebSocket")
            except Exception as e:
                logger.error(f"Failed to start animation: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('stop_animation')
        def handle_stop_animation():
            """Handle stop animation request"""
            try:
                self.flying_notes_renderer.stop_animation()
                self.socketio.emit('animation_stopped', broadcast=True)
                logger.info("Flying notes animation stopped via WebSocket")
            except Exception as e:
                logger.error(f"Failed to stop animation: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('update_settings')
        def handle_update_settings(data):
            """Handle settings update request"""
            try:
                self.flying_notes_renderer.update_settings(data)
                self.socketio.emit('settings_update', self.flying_notes_renderer.get_settings(), broadcast=True)
                logger.info(f"Flying notes settings updated: {data}")
            except Exception as e:
                logger.error(f"Failed to update settings: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('get_settings')
        def handle_get_settings():
            """Handle get settings request"""
            emit('settings_update', self.flying_notes_renderer.get_settings())
        
        @self.socketio.on('sync_position')
        def handle_sync_position(data):
            """Handle MIDI position synchronization"""
            try:
                position = data.get('position', 0)
                self.flying_notes_renderer.sync_with_learn_midi(position)
                logger.debug(f"Synced flying notes position: {position}")
            except Exception as e:
                logger.error(f"Failed to sync position: {e}")
                emit('error', {'message': str(e)})
    
    def broadcast_frame_update(self, frame_data):
        """Broadcast frame update to all connected clients"""
        if self.connected_clients:
            self.socketio.emit('frame_update', frame_data, broadcast=True)
    
    def broadcast_animation_state(self, is_active):
        """Broadcast animation state change"""
        event = 'animation_started' if is_active else 'animation_stopped'
        self.socketio.emit(event, broadcast=True)
    
    def broadcast_settings_update(self, settings):
        """Broadcast settings update to all clients"""
        self.socketio.emit('settings_update', settings, broadcast=True)
    
    def get_socketio(self):
        """Get the SocketIO instance for integration with Flask app"""
        return self.socketio
    
    def run(self, host='127.0.0.1', port=5000, debug=False):
        """Run the WebSocket server"""
        self.socketio.run(self.app, host=host, port=port, debug=debug)


class FlyingNotesWebSocketClient:
    """WebSocket client wrapper for flying notes renderer integration"""
    
    def __init__(self, websocket_handler):
        self.websocket_handler = websocket_handler
    
    def send(self, data):
        """Send data to WebSocket clients"""
        if isinstance(data, str):
            data = json.loads(data)
        
        message_type = data.get('type')
        
        if message_type == 'frame_update':
            self.websocket_handler.broadcast_frame_update(data)
        elif message_type == 'stop':
            self.websocket_handler.broadcast_animation_state(False)
        elif message_type == 'settings_update':
            self.websocket_handler.broadcast_settings_update(data.get('settings', {}))
        else:
            # Generic broadcast
            self.websocket_handler.socketio.emit('message', data, broadcast=True)