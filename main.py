import os
import openai
from transformers import pipeline
import pyautogui
import keyboard
import time
from pathlib import Path
import json
import logging
from typing import Optional, Dict, Any
import asyncio
import websockets
import hmac
import hashlib
import time
import base64
import requests
from datetime import datetime

from config import APIConfig
from ui import UI
from models import (
    Suggestion,
    CodeContext,
    ModelType,
    SuggestionType,
    EditorState,
    Settings
)

class CoinbaseClient:
    def __init__(self, api_key: str, api_secret: str, api_passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        self.base_url = "https://api.pro.coinbase.com"
        
    def get_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        message = f"{timestamp}{method}{request_path}{body}"
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message.encode('ascii'),
            hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')

    def get_headers(self, method: str, request_path: str, body: str = '') -> Dict:
        timestamp = str(int(time.time()))
        signature = self.get_signature(timestamp, method, request_path, body)
        
        return {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-PASSPHRASE': self.api_passphrase,
            'Content-Type': 'application/json'
        }

    def get_account(self) -> Dict:
        method = 'GET'
        request_path = '/accounts'
        headers = self.get_headers(method, request_path)
        response = requests.get(f"{self.base_url}{request_path}", headers=headers)
        return response.json()

    async def websocket_feed(self, product_ids: list, channels: list):
        uri = "wss://ws-feed.pro.coinbase.com"
        
        async with websockets.connect(uri) as websocket:
            timestamp = str(int(time.time()))
            signature = self.get_signature(timestamp, 'GET', '/users/self/verify')
            
            auth_message = {
                'type': 'subscribe',
                'product_ids': product_ids,
                'channels': channels,
                'signature': signature,
                'key': self.api_key,
                'passphrase': self.api_passphrase,
                'timestamp': timestamp
            }
            
            await websocket.send(json.dumps(auth_message))
            
            while True:
                try:
                    message = await websocket.recv()
                    yield json.loads(message)
                except Exception as e:
                    logging.error(f"WebSocket error: {e}")
                    break

class SilentCodingAssistant:
    def __init__(self, config_path: str = "~/.silent_coding/config.json"):
        """Initialize the Silent Coding Assistant."""
        self.setup_logging()
        self.config_path = os.path.expanduser(config_path)
        self.api_config = APIConfig()
        self.setup_openai()
        self.settings = Settings(self.config_path)
        self.ui = UI()
        self.editor_state = EditorState((0, 0), None, None, None)
        self.setup_transformers()
        self.setup_coinbase()
        
    def setup_logging(self):
        """Configure logging system."""
        log_dir = os.path.expanduser('~/.silent_coding')
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=os.path.join(log_dir, 'activity.log')
        )
        self.logger = logging.getLogger(__name__)

    def setup_openai(self):
        """Configure OpenAI client with secure API key handling."""
        api_key = self.api_config.get_api_key()
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.api_config.save_api_key(api_key)
            else:
                raise ValueError("OpenAI API key not found in config or environment variables")
        
        openai.api_key = api_key
        try:
            openai.Model.list()
            self.logger.info("OpenAI API connection successful")
        except Exception as e:
            self.logger.error(f"OpenAI API connection failed: {str(e)}")
            raise

    def setup_coinbase(self):
        """Configure Coinbase CDP client."""
        try:
            api_key = os.getenv('COINBASE_API_KEY')
            api_secret = os.getenv('COINBASE_API_SECRET')
            api_passphrase = os.getenv('COINBASE_API_PASSPHRASE')
            
            if not all([api_key, api_secret, api_passphrase]):
                self.logger.warning("Coinbase API credentials not found. CDP features will be disabled.")
                self.coinbase = None
                return
                
            self.coinbase = CoinbaseClient(api_key, api_secret, api_passphrase)
            self.logger.info("Coinbase CDP integration successful")
            
        except Exception as e:
            self.logger.error(f"Coinbase CDP setup failed: {str(e)}")
            self.coinbase = None

    def setup_transformers(self):
        """Initialize transformer models."""
        try:
            self.code_generator = pipeline("text-generation", model="Salesforce/codegen-350M-mono")
            self.logger.info("Transformer models loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load transformer models: {str(e)}")
            raise

    async def generate_code_suggestion(self, context: str) -> Suggestion:
        """Generate code suggestions using both OpenAI and transformers."""
        try:
            # First try with OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a coding assistant. Provide concise, effective code suggestions."},
                    {"role": "user", "content": f"Suggest code for: {context}"}
                ],
                temperature=self.settings.settings["suggestion_settings"]["temperature"],
                top_p=self.settings.settings["suggestion_settings"]["top_p"]
            )
            openai_suggestion = response.choices[0].message.content

            # Get transformer suggestion
            transformer_suggestion = self.code_generator(
                context, 
                max_length=self.settings.settings["suggestion_settings"]["max_length"]
            )[0]['generated_text']

            # Combine suggestions
            final_content = self.combine_suggestions(openai_suggestion, transformer_suggestion)
            
            return Suggestion(
                content=final_content,
                type=SuggestionType.COMPLETION,
                model=ModelType.COMBINED,
                confidence=0.95,
                metadata={"context": context}
            )
        except Exception as e:
            self.logger.error(f"Error generating code suggestion: {str(e)}")
            return None

    def combine_suggestions(self, openai_sugg: str, transformer_sugg: str) -> str:
        """Combine and select the best parts of both suggestions."""
        # This is a simple implementation - could be made more sophisticated
        if len(openai_sugg) > len(transformer_sugg):
            return openai_sugg
        return transformer_sugg

    async def start_crypto_monitor(self):
        """Start monitoring crypto prices through Coinbase CDP."""
        if not self.coinbase:
            self.logger.warning("Crypto monitoring unavailable - Coinbase CDP not configured")
            return
            
        try:
            product_ids = ['BTC-USD', 'ETH-USD']
            channels = ['ticker']
            
            async for message in self.coinbase.websocket_feed(product_ids, channels):
                if message.get('type') == 'ticker':
                    self.ui.show_notification(
                        f"{message['product_id']}: ${float(message['price']):,.2f}",
                        duration=2000
                    )
        except Exception as e:
            self.logger.error(f"Crypto monitoring error: {str(e)}")

    def start(self):
        """Start the silent coding assistant."""
        self.logger.info("Starting Silent Coding Assistant")
        self.running = True
        
        try:
            keyboard.add_hotkey(
                self.settings.settings['hotkeys']['toggle'],
                self.toggle
            )
            keyboard.add_hotkey(
                self.settings.settings['hotkeys']['generate'],
                self.trigger_suggestion
            )
            
            self.ui.status_bar.show()
            self.ui.update_status("Active", "info")
            
            # Start crypto monitoring in background
            asyncio.create_task(self.start_crypto_monitor())
            
            print("\n=== Silent Coding Legend ===")
            print("Version 1.2.0 - With Coinbase CDP Integration")
            print(f"\nHotkeys:")
            for action, key in self.settings.settings['hotkeys'].items():
                print(f"{action.capitalize()}: {key}")
            print("\nPress 'esc' to exit")
            
            keyboard.wait('esc')
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {str(e)}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources before shutting down."""
        self.running = False
        keyboard.unhook_all()
        self.ui.cleanup()
        self.logger.info("Silent Coding Assistant stopped")

    def toggle(self):
        """Toggle the assistant on/off."""
        self.running = not self.running
        status = "Active" if self.running else "Paused"
        status_type = "info" if self.running else "warning"
        self.ui.update_status(status, status_type)
        self.logger.info(f"Assistant {status.lower()}")

    async def trigger_suggestion(self):
        """Generate and display code suggestion."""
        if not self.running:
            return
            
        try:
            # Get current position and selection
            x, y = pyautogui.position()
            self.editor_state.update_position(x, y)
            
            # Get selected text
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            context = keyboard.get_clipboard_text()
            self.editor_state.update_selection(context)
            
            if context:
                suggestion = await self.generate_code_suggestion(context)
                if suggestion:
                    self.ui.show_suggestion(suggestion.content, x, y)
                    
        except Exception as e:
            self.logger.error(f"Error triggering suggestion: {str(e)}")
            self.ui.show_notification("Error generating suggestion", duration=3000)

def main():
    """Main entry point."""
    try:
        assistant = SilentCodingAssistant()
        asyncio.run(assistant.start())
        
    except Exception as e:
        print(f"Error: {str(e)}")
        logging.error(f"Fatal error: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())