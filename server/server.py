"""
Serveur local pour l'affichage client - Pont entre Flexo 6 et l'ecran client.

Ce serveur :
1. Sert la page web d'affichage client
2. Expose une API REST pour les donnees de transaction
3. Surveille les fichiers de tickets Flexo 6
4. Peut recevoir des mises a jour via API depuis un script externe

Usage: python server.py [--port 5555] [--config ../config/config.json]
"""

import json
import os
import sys
import time
import threading
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# --- Chemins ---
BASE_DIR = Path(__file__).parent.parent.resolve()
DISPLAY_DIR = BASE_DIR / 'display'
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'
DATA_FILE = BASE_DIR / 'config' / 'transaction.json'

# --- Etat global de la transaction ---
transaction_state = {
    'status': 'idle',  # idle, in_progress, payment, completed
    'items': [],
    'subtotal': 0,
    'tax': 0,
    'total': 0,
    'discount': 0,
    'payment_method': '',
    'payment_info': '',
    'last_update': 0,
}

state_lock = threading.Lock()

# --- Configuration ---
config = {
    'store_name': 'Votre Magasin',
    'welcome_message': 'Nous sommes heureux de vous accueillir',
    'thankyou_message': 'A bientot !',
    'thankyou_duration': 5000,
    'logo_url': '',
    'promos': [
        'Bienvenue dans notre magasin !'
    ],
    'colors': {
        'primary': '#1a237e',
        'accent': '#ff6f00',
    },
    'flexo_ticket_path': '',
    'flexo_watch_enabled': False,
}


def load_config():
    """Charge la configuration depuis le fichier JSON."""
    global config
    cfg_path = CONFIG_FILE
    if cfg_path.exists():
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            config.update(user_config)
            print(f'[CONFIG] Configuration chargee depuis {cfg_path}')
        except Exception as e:
            print(f'[CONFIG] Erreur chargement config: {e}')
    else:
        # Creer un fichier de config par defaut
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f'[CONFIG] Fichier de config cree: {cfg_path}')


def save_transaction_state():
    """Sauvegarde l'etat de la transaction dans un fichier."""
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(transaction_state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f'[DATA] Erreur sauvegarde: {e}')


def load_transaction_state():
    """Charge l'etat de la transaction depuis le fichier (si un script externe l'a mis a jour)."""
    global transaction_state
    if DATA_FILE.exists():
        try:
            mtime = DATA_FILE.stat().st_mtime
            if mtime > transaction_state.get('last_update', 0):
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                with state_lock:
                    transaction_state.update(data)
                    transaction_state['last_update'] = mtime
                return True
        except Exception:
            pass
    return False


# --- Surveillance du fichier transaction.json ---
class FileWatcher(threading.Thread):
    """Surveille le fichier transaction.json pour les mises a jour externes."""

    def __init__(self):
        super().__init__(daemon=True)
        self._running = True

    def run(self):
        print('[WATCHER] Surveillance du fichier transaction.json...')
        while self._running:
            load_transaction_state()
            time.sleep(0.3)

    def stop(self):
        self._running = False


# --- Serveur HTTP ---
class CustomerDisplayHandler(SimpleHTTPRequestHandler):
    """Handler HTTP pour servir l'affichage client et l'API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DISPLAY_DIR), **kwargs)

    def log_message(self, format, *args):
        # Silencieux pour les polls frequents
        if '/api/' not in str(args):
            super().log_message(format, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/transaction':
            self._send_json(transaction_state)
        elif path == '/api/config':
            self._send_json(config)
        elif path == '/api/status':
            self._send_json({'status': 'ok', 'version': '1.0.0'})
        else:
            # Servir les fichiers statiques (display/)
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'

        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json({'error': 'JSON invalide'}, 400)
            return

        if path == '/api/transaction':
            self._handle_update_transaction(data)
        elif path == '/api/transaction/item':
            self._handle_add_item(data)
        elif path == '/api/transaction/clear':
            self._handle_clear_transaction()
        elif path == '/api/transaction/payment':
            self._handle_payment(data)
        elif path == '/api/transaction/complete':
            self._handle_complete()
        else:
            self._send_json({'error': 'Route inconnue'}, 404)

    def _handle_update_transaction(self, data):
        """Mise a jour complete de la transaction."""
        with state_lock:
            transaction_state.update(data)
            transaction_state['last_update'] = time.time()
        save_transaction_state()
        self._send_json({'status': 'ok'})

    def _handle_add_item(self, data):
        """Ajouter un article a la transaction."""
        with state_lock:
            if transaction_state['status'] == 'idle':
                transaction_state['status'] = 'in_progress'
                transaction_state['items'] = []
                transaction_state['subtotal'] = 0
                transaction_state['tax'] = 0
                transaction_state['total'] = 0
                transaction_state['discount'] = 0

            item = {
                'description': data.get('description', data.get('name', 'Article')),
                'price': float(data.get('price', 0)),
                'quantity': int(data.get('quantity', 1)),
            }
            transaction_state['items'].append(item)

            # Recalculer les totaux
            subtotal = sum(
                it['price'] * it['quantity'] for it in transaction_state['items']
            )
            discount = float(transaction_state.get('discount', 0))
            tax_rate = 0.20  # TVA 20% par defaut
            taxable = subtotal - discount
            tax = taxable * tax_rate

            transaction_state['subtotal'] = round(subtotal, 2)
            transaction_state['tax'] = round(tax, 2)
            transaction_state['total'] = round(taxable + tax, 2)
            transaction_state['last_update'] = time.time()

        save_transaction_state()
        self._send_json({'status': 'ok', 'item_count': len(transaction_state['items'])})

    def _handle_clear_transaction(self):
        """Remettre a zero la transaction."""
        with state_lock:
            transaction_state['status'] = 'idle'
            transaction_state['items'] = []
            transaction_state['subtotal'] = 0
            transaction_state['tax'] = 0
            transaction_state['total'] = 0
            transaction_state['discount'] = 0
            transaction_state['payment_method'] = ''
            transaction_state['payment_info'] = ''
            transaction_state['last_update'] = time.time()
        save_transaction_state()
        self._send_json({'status': 'ok'})

    def _handle_payment(self, data):
        """Passer en mode paiement."""
        with state_lock:
            transaction_state['status'] = 'payment'
            transaction_state['payment_method'] = data.get('method', '')
            transaction_state['payment_info'] = data.get('info', '')
            transaction_state['last_update'] = time.time()
        save_transaction_state()
        self._send_json({'status': 'ok'})

    def _handle_complete(self):
        """Marquer la transaction comme terminee."""
        with state_lock:
            transaction_state['status'] = 'completed'
            transaction_state['last_update'] = time.time()
        save_transaction_state()

        # Auto-reset apres un delai
        def auto_reset():
            time.sleep(config.get('thankyou_duration', 5000) / 1000)
            with state_lock:
                transaction_state['status'] = 'idle'
                transaction_state['items'] = []
                transaction_state['subtotal'] = 0
                transaction_state['tax'] = 0
                transaction_state['total'] = 0
                transaction_state['discount'] = 0
                transaction_state['payment_method'] = ''
                transaction_state['payment_info'] = ''
                transaction_state['last_update'] = time.time()
            save_transaction_state()

        threading.Thread(target=auto_reset, daemon=True).start()
        self._send_json({'status': 'ok'})

    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description='Serveur affichage client')
    parser.add_argument('--port', type=int, default=5555, help='Port du serveur (defaut: 5555)')
    parser.add_argument('--config', type=str, default=None, help='Chemin du fichier de config')
    args = parser.parse_args()

    global CONFIG_FILE
    if args.config:
        CONFIG_FILE = Path(args.config).resolve()

    load_config()

    # Demarrer la surveillance du fichier
    watcher = FileWatcher()
    watcher.start()

    # Demarrer le serveur HTTP
    server = HTTPServer(('0.0.0.0', args.port), CustomerDisplayHandler)
    print(f'')
    print(f'  ======================================')
    print(f'  AFFICHAGE CLIENT - Serveur demarre')
    print(f'  ======================================')
    print(f'  URL locale:  http://localhost:{args.port}')
    print(f'  Mode demo:   http://localhost:{args.port}?demo=1')
    print(f'  API status:  http://localhost:{args.port}/api/status')
    print(f'  ======================================')
    print(f'')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[SERVER] Arret du serveur...')
        watcher.stop()
        server.shutdown()


if __name__ == '__main__':
    main()
