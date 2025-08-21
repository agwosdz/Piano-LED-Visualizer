import asyncio
import atexit
import threading

from waitress import serve

import webinterface as web_mod
from lib.log_setup import logger
from webinterface import webinterface, app_state
from lib.flying_notes_renderer import FlyingNotesRenderer
from lib.websocket_handler import WebSocketHandler


class WebInterfaceManager:
    def __init__(self, args, usersettings, ledsettings, ledstrip, learning, saving, midiports, menu, hotspot, platform, usb_gadget):
        self.args = args
        self.usersettings = usersettings
        self.ledsettings = ledsettings
        self.ledstrip = ledstrip
        self.learning = learning
        self.saving = saving
        self.midiports = midiports
        self.menu = menu
        self.hotspot = hotspot
        self.platform = platform
        self.usb_gadget = usb_gadget
        self.websocket_loop = asyncio.new_event_loop()
        self.setup_web_interface()

    def setup_web_interface(self):
        if self.args.webinterface != "false":
            logger.info('Starting webinterface')

            app_state.usersettings = self.usersettings
            app_state.ledsettings = self.ledsettings
            app_state.ledstrip = self.ledstrip
            app_state.learning = self.learning
            app_state.saving = self.saving
            app_state.midiports = self.midiports
            app_state.menu = self.menu
            app_state.hotspot = self.hotspot
            app_state.platform = self.platform
            app_state.usb_midi_gadget = self.usb_gadget

            # Initialize flying notes components
            self._initialize_flying_notes()

            webinterface.jinja_env.auto_reload = True
            webinterface.config['TEMPLATES_AUTO_RELOAD'] = True

            if not self.args.port:
                self.args.port = 80

            processThread = threading.Thread(
                target=serve,
                args=(webinterface,),
                kwargs={'host': '0.0.0.0', 'port': self.args.port, 'threads': 20},
                daemon=True
            )
            processThread.start()

            processThread = threading.Thread(
                target=web_mod.start_server,
                args=(self.websocket_loop,),
                daemon=True
            )
            processThread.start()

            atexit.register(web_mod.stop_server, self.websocket_loop)
    
    def _initialize_flying_notes(self):
        """Initialize flying notes renderer and WebSocket handler"""
        try:
            # Import views module to access global instances
            import webinterface.views as views
            
            # Initialize flying notes renderer
            views.flying_notes_renderer = FlyingNotesRenderer(self.usersettings, self.learning)
            
            # Initialize WebSocket handler
            views.websocket_handler = WebSocketHandler(webinterface, views.flying_notes_renderer)
            
            logger.info('Flying notes components initialized successfully')
            
        except Exception as e:
            logger.error(f'Failed to initialize flying notes components: {str(e)}')
