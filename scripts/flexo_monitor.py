"""
Moniteur Flexo 6 - Surveille les tickets et met a jour l'affichage client.

Ce script surveille les fichiers de tickets generes par Flexo 6
et envoie les donnees au serveur d'affichage client via API.

Strategies de detection supportees :
1. Surveillance d'un dossier de tickets (fichiers texte/CSV)
2. Surveillance d'un fichier de ticket en cours (ecrit par Flexo)
3. Surveillance de la base de donnees Flexo (SQLite/Access)

Adaptez les chemins et le format selon votre configuration Flexo 6.
"""

import json
import os
import sys
import time
import re
import urllib.request
from pathlib import Path
from datetime import datetime

# --- Configuration ---
BASE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'

SERVER_URL = 'http://localhost:5555'

# Chemins typiques de Flexo 6 (a adapter selon votre installation)
FLEXO_PATHS = {
    'ticket_dir': r'C:\Flexo6\Tickets',
    'current_ticket': r'C:\Flexo6\Data\ticket_en_cours.txt',
    'export_dir': r'C:\Flexo6\Export',
    # Autre chemin possible
    'program_data': r'C:\ProgramData\Flexo6\Tickets',
}


def load_config():
    """Charge la config pour obtenir les chemins Flexo."""
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
        print(f'[MONITOR] Erreur envoi: {e}')
        return None


def parse_flexo_ticket_line(line):
    """
    Parse une ligne de ticket Flexo 6.

    Flexo 6 genere typiquement des fichiers avec le format :
    - Lignes d'articles : CODE;DESCRIPTION;QTE;PRIX_UNIT;TOTAL
    - Ou format texte : DESCRIPTION    QTE x PRIX   TOTAL

    Adaptez cette fonction selon le format exact de votre Flexo 6.
    """
    line = line.strip()
    if not line:
        return None

    # Format CSV avec point-virgule (courant Flexo)
    if ';' in line:
        parts = line.split(';')
        if len(parts) >= 4:
            try:
                return {
                    'code': parts[0].strip(),
                    'description': parts[1].strip(),
                    'quantity': int(float(parts[2].strip() or '1')),
                    'price': float(parts[3].strip().replace(',', '.')),
                }
            except (ValueError, IndexError):
                pass

    # Format tabule
    if '\t' in line:
        parts = line.split('\t')
        if len(parts) >= 3:
            try:
                return {
                    'description': parts[0].strip(),
                    'quantity': int(float(parts[1].strip() or '1')),
                    'price': float(parts[2].strip().replace(',', '.')),
                }
            except (ValueError, IndexError):
                pass

    # Format texte avec espaces (fallback)
    match = re.match(
        r'^(.+?)\s+(\d+)\s*x\s*([\d,\.]+)\s+([\d,\.]+)$',
        line, re.IGNORECASE
    )
    if match:
        return {
            'description': match.group(1).strip(),
            'quantity': int(match.group(2)),
            'price': float(match.group(3).replace(',', '.')),
        }

    return None


def parse_flexo_ticket_file(filepath):
    """Parse un fichier de ticket complet."""
    items = []
    try:
        # Essayer plusieurs encodages (Windows)
        for encoding in ['utf-8', 'cp1252', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue
        else:
            return items

        for line in lines:
            item = parse_flexo_ticket_line(line)
            if item:
                items.append(item)
    except Exception as e:
        print(f'[MONITOR] Erreur lecture ticket: {e}')

    return items


class FlexoMonitor:
    """Surveille les fichiers Flexo 6 et met a jour l'affichage client."""

    def __init__(self):
        self.config = load_config()
        self.ticket_path = self._find_ticket_path()
        self.last_mtime = 0
        self.last_files = set()
        self.current_items = []
        self.is_active = False

    def _find_ticket_path(self):
        """Trouve le dossier de tickets Flexo 6."""
        # Priorite au chemin configure
        configured = self.config.get('flexo_ticket_path', '')
        if configured and os.path.exists(configured):
            print(f'[MONITOR] Dossier tickets: {configured}')
            return Path(configured)

        # Chercher dans les chemins connus
        for name, path in FLEXO_PATHS.items():
            if os.path.exists(path):
                print(f'[MONITOR] Dossier tickets trouve: {path}')
                return Path(path)

        print('[MONITOR] ATTENTION: Aucun dossier de tickets Flexo 6 trouve.')
        print('[MONITOR] Configurez "flexo_ticket_path" dans config/config.json')
        print('[MONITOR] Le moniteur surveillera le fichier transaction.json a la place.')
        return None

    def watch_ticket_directory(self):
        """Surveille un dossier pour les nouveaux fichiers de tickets."""
        if not self.ticket_path or not self.ticket_path.is_dir():
            return False

        current_files = set()
        try:
            for f in self.ticket_path.iterdir():
                if f.is_file() and f.suffix.lower() in ('.txt', '.csv', '.dat', '.tck'):
                    current_files.add(f.name)
        except PermissionError:
            return False

        # Detecter les nouveaux fichiers
        new_files = current_files - self.last_files
        self.last_files = current_files

        if new_files:
            # Traiter le fichier le plus recent
            newest = max(
                [self.ticket_path / f for f in new_files],
                key=lambda p: p.stat().st_mtime
            )
            items = parse_flexo_ticket_file(newest)
            if items:
                self._send_full_transaction(items)
                return True

        return False

    def watch_single_file(self):
        """Surveille un seul fichier de ticket en cours."""
        if not self.ticket_path or not self.ticket_path.is_file():
            return False

        try:
            mtime = self.ticket_path.stat().st_mtime
            if mtime <= self.last_mtime:
                return False

            self.last_mtime = mtime
            items = parse_flexo_ticket_file(self.ticket_path)

            if items and items != self.current_items:
                # De nouveaux articles ont ete ajoutes
                if len(items) > len(self.current_items):
                    for item in items[len(self.current_items):]:
                        send_to_server('transaction/item', item)
                else:
                    # Le fichier a ete reecrit, envoyer tout
                    self._send_full_transaction(items)

                self.current_items = items[:]
                return True

            elif not items and self.current_items:
                # Le fichier est vide = transaction terminee
                send_to_server('transaction/complete')
                self.current_items = []
                return True

        except FileNotFoundError:
            if self.current_items:
                send_to_server('transaction/complete')
                self.current_items = []
        except Exception as e:
            print(f'[MONITOR] Erreur: {e}')

        return False

    def _send_full_transaction(self, items):
        """Envoie une transaction complete au serveur."""
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
        """Boucle principale de surveillance."""
        print('')
        print('  ======================================')
        print('  MONITEUR FLEXO 6 - Demarre')
        print('  ======================================')

        if not self.ticket_path:
            print('  Mode: Surveillance transaction.json')
            print('  (Le serveur gere les mises a jour)')
            print('  ======================================')
            print('')
            # Pas de dossier Flexo, le serveur surveille transaction.json
            # On reste en vie juste au cas ou
            while True:
                time.sleep(10)
            return

        is_dir = self.ticket_path.is_dir()
        mode = 'dossier' if is_dir else 'fichier'
        print(f'  Mode: Surveillance {mode}')
        print(f'  Chemin: {self.ticket_path}')
        print('  ======================================')
        print('')

        while True:
            try:
                if is_dir:
                    self.watch_ticket_directory()
                else:
                    self.watch_single_file()
            except Exception as e:
                print(f'[MONITOR] Erreur: {e}')

            time.sleep(0.5)


def main():
    monitor = FlexoMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        print('\n[MONITOR] Arret.')


if __name__ == '__main__':
    main()
