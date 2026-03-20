"""
Moniteur Flexo 6 - Capture en TEMPS REEL des produits scannes.

Strategies de capture (du plus rapide au plus lent) :
1. CAPTURE CLAVIER : intercepte les codes-barres du scanner
   (le scanner agit comme un clavier, on capte les frappes)
2. BASE FIREBIRD : interroge la base Flexo 6 pour la transaction ouverte
3. FICHIER JSON : mode manuel via transaction.json

Le script detecte automatiquement la meilleure methode disponible.
"""

import json
import os
import sys
import time
import re
import threading
import urllib.request
from pathlib import Path
from datetime import datetime

# --- Configuration ---
BASE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'
PRODUCTS_DB_FILE = BASE_DIR / 'config' / 'products.json'

SERVER_URL = 'http://localhost:5555'

# Delai max entre deux touches pour considerer que c'est un scan (ms)
BARCODE_MAX_DELAY_MS = 80
# Longueur min d'un code-barres (EAN-8 = 8, EAN-13 = 13)
BARCODE_MIN_LENGTH = 4


def load_config():
    """Charge la configuration."""
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    return config


def send_to_server(endpoint, data=None):
    """Envoie une requete POST au serveur local."""
    url = f'{SERVER_URL}/api/{endpoint}'
    payload = json.dumps(data or {}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'[MONITOR] Erreur envoi serveur: {e}')
        return None


# =============================================================
# STRATEGIE 1 : CAPTURE CLAVIER (Scanner code-barres)
# =============================================================

class BarcodeScannerCapture:
    """
    Capture les codes-barres en interceptant les frappes clavier.

    Un scanner code-barres envoie les caracteres tres rapidement
    (< 50ms entre chaque touche) puis un Entree.
    On detecte cette sequence rapide pour distinguer un scan
    d'une saisie manuelle.
    """

    def __init__(self, product_lookup, on_barcode):
        self.product_lookup = product_lookup
        self.on_barcode = on_barcode
        self.buffer = []
        self.last_key_time = 0
        self.available = False

        # Tenter d'importer pynput (capture clavier)
        try:
            from pynput import keyboard
            self.keyboard = keyboard
            self.available = True
            print('[SCANNER] Module pynput disponible - capture clavier active')
        except ImportError:
            print('[SCANNER] Module pynput non installe.')
            print('[SCANNER] Pour activer la capture scanner:')
            print('[SCANNER]   pip install pynput')
            self.available = False

    def start(self):
        if not self.available:
            return False

        listener = self.keyboard.Listener(on_press=self._on_key_press)
        listener.daemon = True
        listener.start()
        print('[SCANNER] Ecoute du scanner code-barres active...')
        return True

    def _on_key_press(self, key):
        now = time.time() * 1000  # ms

        try:
            char = key.char
        except AttributeError:
            # Touche speciale
            if key == self.keyboard.Key.enter:
                self._process_buffer()
            elif key == self.keyboard.Key.tab:
                self._process_buffer()
            else:
                # Autre touche speciale, reset le buffer
                if now - self.last_key_time > BARCODE_MAX_DELAY_MS:
                    self.buffer = []
            self.last_key_time = now
            return

        # Touche normale
        if now - self.last_key_time > BARCODE_MAX_DELAY_MS and self.buffer:
            # Trop de temps entre les touches, c'est une saisie manuelle
            self.buffer = []

        self.buffer.append(char)
        self.last_key_time = now

    def _process_buffer(self):
        """Traite le buffer quand un Entree est detecte."""
        if len(self.buffer) < BARCODE_MIN_LENGTH:
            self.buffer = []
            return

        barcode = ''.join(self.buffer)
        self.buffer = []

        # Verifier que ca ressemble a un code-barres
        # (principalement des chiffres pour EAN)
        if barcode.isdigit() or re.match(r'^[A-Za-z0-9\-]+$', barcode):
            print(f'[SCANNER] Code-barres detecte: {barcode}')
            self.on_barcode(barcode)


# =============================================================
# STRATEGIE 2 : BASE DE DONNEES FIREBIRD (Flexo 6)
# =============================================================

class FlexoFirebirdMonitor:
    """
    Interroge la base de donnees Firebird de Flexo 6
    pour lire la transaction en cours en temps reel.
    """

    def __init__(self):
        self.available = False
        self.connection = None
        self.db_path = None
        self.last_item_count = 0
        self.last_items_hash = ''

        # Tenter d'importer le driver Firebird
        try:
            import firebirdsql
            self.fdb = firebirdsql
            print('[FIREBIRD] Module firebirdsql disponible')
            self.available = True
        except ImportError:
            try:
                import fdb
                self.fdb = fdb
                print('[FIREBIRD] Module fdb disponible')
                self.available = True
            except ImportError:
                print('[FIREBIRD] Module Firebird non installe.')
                print('[FIREBIRD] Pour activer la connexion Flexo:')
                print('[FIREBIRD]   pip install firebirdsql')
                self.available = False

    def find_database(self, config):
        """Trouve la base de donnees Flexo 6."""
        # Chemin configure
        db_path = config.get('flexo_db_path', '')
        if db_path and os.path.exists(db_path):
            self.db_path = db_path
            return True

        # Chercher dans les emplacements typiques
        search_paths = [
            r'C:\Flexo6',
            r'C:\Program Files\Flexo6',
            r'C:\Program Files (x86)\Flexo6',
            r'C:\ProgramData\Flexo6',
            r'C:\Program Files\Data-Concept\Flexo6',
            r'C:\Program Files (x86)\Data-Concept\Flexo6',
            r'D:\Flexo6',
        ]

        for base in search_paths:
            if not os.path.exists(base):
                continue
            # Chercher les fichiers .fdb (Firebird)
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.lower().endswith(('.fdb', '.gdb')):
                        self.db_path = os.path.join(root, f)
                        print(f'[FIREBIRD] Base trouvee: {self.db_path}')
                        return True

        print('[FIREBIRD] Base Flexo 6 non trouvee.')
        print('[FIREBIRD] Configurez "flexo_db_path" dans config/config.json')
        return False

    def connect(self, config):
        """Se connecte a la base Firebird."""
        if not self.available or not self.db_path:
            return False

        try:
            host = config.get('flexo_db_host', 'localhost')
            port = config.get('flexo_db_port', 3050)
            user = config.get('flexo_db_user', 'SYSDBA')
            password = config.get('flexo_db_password', 'masterkey')

            self.connection = self.fdb.connect(
                host=host,
                port=port,
                database=self.db_path,
                user=user,
                password=password,
                charset='UTF8',
            )
            print(f'[FIREBIRD] Connecte a {self.db_path}')
            return True
        except Exception as e:
            print(f'[FIREBIRD] Erreur connexion: {e}')
            # Essayer en embedded (mono-poste)
            try:
                self.connection = self.fdb.connect(
                    database=self.db_path,
                    user='SYSDBA',
                    password='masterkey',
                    charset='UTF8',
                )
                print(f'[FIREBIRD] Connecte en mode embedded')
                return True
            except Exception as e2:
                print(f'[FIREBIRD] Erreur connexion embedded: {e2}')
                return False

    def poll_current_transaction(self):
        """
        Interroge la base pour la transaction/ticket en cours.

        NOTE: Les noms de tables ci-dessous sont des noms typiques
        pour un logiciel de caisse. Vous devrez peut-etre les adapter
        selon votre installation Flexo 6.

        Pour trouver les bonnes tables, executez le script
        scripts/explorer_base.py
        """
        if not self.connection:
            return None

        try:
            cursor = self.connection.cursor()

            # Essayer plusieurs noms de tables courants pour les lignes de ticket
            table_queries = [
                # Format: (query, description)
                ("""
                    SELECT l.DESIGNATION, l.QUANTITE, l.PU_TTC, l.MONTANT_TTC
                    FROM LIGNES_TICKET l
                    JOIN TICKETS t ON l.ID_TICKET = t.ID_TICKET
                    WHERE t.ETAT = 0
                    ORDER BY l.NUM_LIGNE
                """, "LIGNES_TICKET / TICKETS"),
                ("""
                    SELECT l.LIBELLE, l.QTE, l.PRIX_UNIT, l.TOTAL
                    FROM LIGNE_VENTE l
                    JOIN VENTE v ON l.ID_VENTE = v.ID_VENTE
                    WHERE v.STATUT = 0
                    ORDER BY l.ORDRE
                """, "LIGNE_VENTE / VENTE"),
                ("""
                    SELECT l.DESCRIPTION, l.QUANTITE, l.PRIX, l.MONTANT
                    FROM DETAIL_TICKET l
                    JOIN TICKET_ENCOURS t ON l.TICKET_ID = t.ID
                    ORDER BY l.LIGNE
                """, "DETAIL_TICKET / TICKET_ENCOURS"),
                ("""
                    SELECT l.NOM_ARTICLE, l.QTE, l.PRIX_TTC, l.TOTAL_TTC
                    FROM PANIER l
                    WHERE l.STATUT = 'EN_COURS'
                    ORDER BY l.ID
                """, "PANIER"),
            ]

            for query, desc in table_queries:
                try:
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    items = []
                    for row in rows:
                        items.append({
                            'description': str(row[0] or ''),
                            'quantity': int(row[1] or 1),
                            'price': float(row[2] or 0),
                        })
                    # Si on arrive ici, la requete a fonctionne
                    return items
                except Exception:
                    continue

            return None

        except Exception as e:
            print(f'[FIREBIRD] Erreur requete: {e}')
            # Reconnexion
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
            return None


# =============================================================
# BASE DE PRODUITS LOCALE (pour recherche par code-barres)
# =============================================================

class ProductDatabase:
    """
    Base de produits locale pour associer un code-barres a un produit.
    Peut etre alimentee depuis Flexo ou manuellement.
    """

    def __init__(self):
        self.products = {}
        self._load()

    def _load(self):
        """Charge la base de produits locale."""
        if PRODUCTS_DB_FILE.exists():
            try:
                with open(PRODUCTS_DB_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for p in data:
                        code = p.get('code', p.get('barcode', ''))
                        if code:
                            self.products[str(code)] = p
                elif isinstance(data, dict):
                    self.products = data
                print(f'[PRODUITS] {len(self.products)} produits charges')
            except Exception as e:
                print(f'[PRODUITS] Erreur chargement: {e}')
        else:
            print(f'[PRODUITS] Pas de base locale ({PRODUCTS_DB_FILE})')
            print(f'[PRODUITS] Les articles seront affiches avec le code-barres')
            self._create_sample()

    def _create_sample(self):
        """Cree un fichier exemple."""
        sample = [
            {"code": "3017620422003", "description": "Nutella 400g", "price": 3.95},
            {"code": "3228857000166", "description": "Cristaline 1.5L", "price": 0.50},
            {"code": "3175681851856", "description": "Baguette tradition", "price": 1.30},
        ]
        try:
            PRODUCTS_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(PRODUCTS_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(sample, f, indent=2, ensure_ascii=False)
            print(f'[PRODUITS] Fichier exemple cree: {PRODUCTS_DB_FILE}')
        except Exception:
            pass

    def lookup(self, barcode):
        """Cherche un produit par code-barres."""
        product = self.products.get(str(barcode))
        if product:
            return {
                'description': product.get('description', product.get('name', barcode)),
                'price': float(product.get('price', 0)),
                'quantity': 1,
                'barcode': barcode,
            }
        # Produit inconnu - afficher le code
        return {
            'description': f'Article ({barcode})',
            'price': 0,
            'quantity': 1,
            'barcode': barcode,
        }

    def lookup_from_firebird(self, barcode, fb_monitor):
        """Cherche un produit dans la base Firebird de Flexo."""
        if not fb_monitor or not fb_monitor.connection:
            return None

        try:
            cursor = fb_monitor.connection.cursor()
            queries = [
                ("""
                    SELECT DESIGNATION, PV_TTC FROM ARTICLES
                    WHERE CODE_BARRE = ?
                """, "ARTICLES.CODE_BARRE"),
                ("""
                    SELECT LIBELLE, PRIX_TTC FROM PRODUIT
                    WHERE EAN = ?
                """, "PRODUIT.EAN"),
                ("""
                    SELECT NOM, PRIX_VENTE FROM ARTICLE
                    WHERE CODE_BARRES = ?
                """, "ARTICLE.CODE_BARRES"),
            ]

            for query, desc in queries:
                try:
                    cursor.execute(query, (barcode,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            'description': str(row[0] or ''),
                            'price': float(row[1] or 0),
                            'quantity': 1,
                            'barcode': barcode,
                        }
                except Exception:
                    continue

        except Exception as e:
            print(f'[FIREBIRD] Erreur recherche produit: {e}')

        return None


# =============================================================
# MONITEUR PRINCIPAL
# =============================================================

class FlexoRealtimeMonitor:
    """
    Moniteur principal qui combine les strategies de capture.
    """

    def __init__(self):
        self.config = load_config()
        self.product_db = ProductDatabase()
        self.fb_monitor = FlexoFirebirdMonitor()
        self.scanner = BarcodeScannerCapture(
            product_lookup=self._lookup_product,
            on_barcode=self._on_barcode_scanned,
        )
        self.last_fb_items_count = 0

    def _lookup_product(self, barcode):
        """Cherche un produit dans toutes les sources disponibles."""
        # 1. Essayer la base Firebird
        if self.fb_monitor.connection:
            product = self.product_db.lookup_from_firebird(barcode, self.fb_monitor)
            if product and product['price'] > 0:
                return product

        # 2. Essayer la base locale
        return self.product_db.lookup(barcode)

    def _on_barcode_scanned(self, barcode):
        """Callback quand un code-barres est scanne."""
        product = self._lookup_product(barcode)
        if product:
            print(f'[SCAN] {product["description"]} - {product["price"]} EUR')
            send_to_server('transaction/item', product)
        else:
            print(f'[SCAN] Produit inconnu: {barcode}')
            send_to_server('transaction/item', {
                'description': f'Article ({barcode})',
                'price': 0,
                'quantity': 1,
            })

    def _poll_firebird(self):
        """Polling de la base Firebird pour la transaction en cours."""
        items = self.fb_monitor.poll_current_transaction()
        if items is None:
            return

        if len(items) != self.last_fb_items_count:
            self.last_fb_items_count = len(items)

            if len(items) == 0:
                # Transaction terminee/annulee
                send_to_server('transaction/clear')
                return

            # Calculer les totaux
            subtotal = sum(it['price'] * it['quantity'] for it in items)
            tax_rate = self.config.get('tax_rate', 0.20)
            tax = subtotal * tax_rate

            send_to_server('transaction', {
                'status': 'in_progress',
                'items': items,
                'subtotal': round(subtotal, 2),
                'tax': round(tax, 2),
                'total': round(subtotal + tax, 2),
                'discount': 0,
            })

    def run(self):
        """Boucle principale."""
        print('')
        print('  ================================================')
        print('  MONITEUR FLEXO 6 - Capture temps reel')
        print('  ================================================')

        strategies = []

        # Strategie 1 : Capture scanner
        if self.scanner.available:
            self.scanner.start()
            strategies.append('Capture scanner (clavier)')

        # Strategie 2 : Base Firebird
        if self.fb_monitor.available:
            if self.fb_monitor.find_database(self.config):
                if self.fb_monitor.connect(self.config):
                    strategies.append('Base Firebird Flexo 6')

        if not strategies:
            strategies.append('Fichier transaction.json (manuel/API)')

        print(f'  Strategies actives:')
        for s in strategies:
            print(f'    - {s}')
        print('  ================================================')
        print('')

        if not self.scanner.available:
            print('')
            print('  CONSEIL: Installez pynput pour la capture scanner:')
            print('    pip install pynput')
            print('')

        # Boucle de polling
        while True:
            try:
                # Polling Firebird si connecte
                if self.fb_monitor.connection:
                    self._poll_firebird()
            except Exception as e:
                print(f'[MONITOR] Erreur: {e}')

            time.sleep(0.5)


def main():
    monitor = FlexoRealtimeMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print('\n[MONITOR] Arret.')


if __name__ == '__main__':
    main()
