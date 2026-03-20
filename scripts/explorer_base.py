"""
Explorateur de base de donnees Flexo 6.

Ce script vous aide a decouvrir les tables et colonnes
de votre base Firebird Flexo 6, afin d'adapter le moniteur.

Usage: python explorer_base.py [chemin_vers_fichier.fdb]
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_FILE = BASE_DIR / 'config' / 'config.json'


def find_firebird_driver():
    """Trouve le driver Firebird disponible."""
    try:
        import firebirdsql
        return firebirdsql
    except ImportError:
        pass
    try:
        import fdb
        return fdb
    except ImportError:
        pass
    print('ERREUR: Aucun driver Firebird installe.')
    print('Installez-en un avec:')
    print('  pip install firebirdsql')
    print('  ou')
    print('  pip install fdb')
    sys.exit(1)


def main():
    config = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # Trouver le fichier de base
    db_path = None
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = config.get('flexo_db_path', '')

    if not db_path:
        print('Usage: python explorer_base.py <chemin_fichier.fdb>')
        print('')
        print('Ou configurez "flexo_db_path" dans config/config.json')
        print('')
        print('Emplacements courants a verifier:')
        paths = [
            r'C:\Flexo6',
            r'C:\Program Files\Flexo6',
            r'C:\Program Files (x86)\Flexo6',
            r'C:\ProgramData\Flexo6',
            r'C:\Program Files\Data-Concept',
        ]
        for p in paths:
            exists = '[EXISTE]' if os.path.exists(p) else '[      ]'
            print(f'  {exists} {p}')
        return

    fdb = find_firebird_driver()

    host = config.get('flexo_db_host', 'localhost')
    port = config.get('flexo_db_port', 3050)
    user = config.get('flexo_db_user', 'SYSDBA')
    password = config.get('flexo_db_password', 'masterkey')

    print(f'Connexion a {db_path}...')

    try:
        conn = fdb.connect(
            host=host, port=port,
            database=db_path,
            user=user, password=password,
            charset='UTF8',
        )
    except Exception as e:
        print(f'Erreur connexion serveur: {e}')
        print('Tentative en mode embedded...')
        try:
            conn = fdb.connect(
                database=db_path,
                user=user, password=password,
                charset='UTF8',
            )
        except Exception as e2:
            print(f'Erreur: {e2}')
            return

    print('Connecte !\n')

    cursor = conn.cursor()

    # Lister toutes les tables
    cursor.execute("""
        SELECT RDB$RELATION_NAME
        FROM RDB$RELATIONS
        WHERE RDB$SYSTEM_FLAG = 0
        ORDER BY RDB$RELATION_NAME
    """)
    tables = [row[0].strip() for row in cursor.fetchall()]

    print(f'=== {len(tables)} TABLES TROUVEES ===\n')

    # Mots-cles interessants pour une caisse
    keywords = [
        'TICKET', 'VENTE', 'LIGNE', 'ARTICLE', 'PRODUIT', 'CAISSE',
        'PANIER', 'ENCAISS', 'CLIENT', 'ENCOURS', 'DETAIL', 'FACTURE',
        'REGLEMENT', 'PAIEMENT', 'MOUVEMENT', 'STOCK', 'BARR', 'EAN',
    ]

    interesting = []
    other = []

    for table in tables:
        is_interesting = any(kw in table.upper() for kw in keywords)
        if is_interesting:
            interesting.append(table)
        else:
            other.append(table)

    if interesting:
        print('--- Tables liees a la caisse (probables) ---')
        for t in interesting:
            print(f'  * {t}')
            # Afficher les colonnes
            cursor.execute(f"""
                SELECT RDB$FIELD_NAME
                FROM RDB$RELATION_FIELDS
                WHERE RDB$RELATION_NAME = '{t}'
                ORDER BY RDB$FIELD_POSITION
            """)
            cols = [row[0].strip() for row in cursor.fetchall()]
            for c in cols:
                print(f'      - {c}')
            # Afficher quelques lignes
            try:
                cursor.execute(f'SELECT FIRST 3 * FROM "{t}"')
                rows = cursor.fetchall()
                if rows:
                    print(f'      Exemple ({len(rows)} lignes):')
                    for row in rows:
                        vals = [str(v)[:40] if v is not None else 'NULL' for v in row]
                        print(f'        {vals}')
            except Exception:
                print(f'      (lecture impossible)')
            print()

    if other:
        print('\n--- Autres tables ---')
        for t in other:
            print(f'  {t}')

    # Sauvegarder le schema
    schema_file = BASE_DIR / 'config' / 'schema_flexo.json'
    schema = {}
    for t in tables:
        cursor.execute(f"""
            SELECT RDB$FIELD_NAME
            FROM RDB$RELATION_FIELDS
            WHERE RDB$RELATION_NAME = '{t}'
            ORDER BY RDB$FIELD_POSITION
        """)
        schema[t] = [row[0].strip() for row in cursor.fetchall()]

    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f'\nSchema sauvegarde dans {schema_file}')

    conn.close()
    print('\nTermine !')


if __name__ == '__main__':
    main()
