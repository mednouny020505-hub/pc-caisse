# Affichage Client Double Ecran - Caisse Flexo 6

Solution d'affichage client **en temps reel** sur le deuxieme ecran de votre caisse enregistreuse sous Flexo 6 / Windows 10.

Les produits s'affichent au moment ou ils sont scannes, **avant** la creation du ticket.

## Fonctionnalites

- **Capture temps reel** : les articles s'affichent des qu'ils sont scannes
- **Ecran d'accueil** : logo, nom du magasin, messages promotionnels rotatifs, horloge
- **Ecran de transaction** : articles en temps reel, dernier article scanne en grand, totaux
- **Ecran de paiement** : montant a payer, mode de paiement
- **Ecran de remerciement** : animation de confirmation apres paiement
- **Mode demo** : test complet sans Flexo 6

## Comment ca marche

Le systeme utilise **2 strategies combinees** pour afficher les produits en temps reel :

1. **Capture scanner code-barres** (via `pynput`) : le scanner agit comme un clavier, on intercepte les frappes rapides pour detecter les codes-barres
2. **Base de donnees Firebird** (Flexo 6) : interrogation directe de la base pour lire la transaction en cours

Les deux strategies fonctionnent ensemble pour une couverture maximale.

## Pre-requis

- Windows 10
- Python 3.8+ (telecharger sur https://www.python.org/downloads/)
  - **IMPORTANT** : cocher "Add Python to PATH" lors de l'installation
- Google Chrome ou Microsoft Edge (pour le mode kiosque plein ecran)
- Double ecran configure dans les parametres d'affichage Windows

## Installation rapide

1. Copiez le dossier `pc-caisse` sur votre PC de caisse (ex: `C:\pc-caisse`)

2. Double-cliquez sur `scripts\lancer-affichage.bat` - les dependances s'installent automatiquement

3. C'est pret ! Le script installe `pynput` (capture scanner) et `firebirdsql` (base Flexo) automatiquement.

## Configuration

Editez `config/config.json` :

```json
{
  "store_name": "Mon Magasin",
  "welcome_message": "Bienvenue chez nous !",
  "promos": ["Promo du jour : -20% sur les fruits !"],

  "flexo_db_path": "C:\\Flexo6\\Data\\FLEXO.FDB",
  "flexo_db_host": "localhost",
  "flexo_db_port": 3050,
  "flexo_db_user": "SYSDBA",
  "flexo_db_password": "masterkey"
}
```

### Trouver votre base Flexo 6

Pour decouvrir ou se trouve votre base de donnees et quelles tables utiliser :

```batch
python scripts\explorer_base.py C:\Flexo6\Data\FLEXO.FDB
```

Ce script liste toutes les tables et colonnes de votre base et sauvegarde le schema dans `config/schema_flexo.json`.

### Base de produits locale

Si la connexion Firebird n'est pas possible, vous pouvez utiliser une base de produits locale. Editez `config/products.json` :

```json
[
  {"code": "3017620422003", "description": "Nutella 400g", "price": 3.95},
  {"code": "3228857000166", "description": "Cristaline 1.5L", "price": 0.50}
]
```

## Utilisation

### Mode demo (pour tester)
```batch
scripts\ouvrir-demo.bat
```

### Mode production
```batch
scripts\lancer-affichage.bat
```

Ce script :
1. Installe les dependances Python (`pynput`, `firebirdsql`)
2. Demarre le serveur local (port 5555)
3. Demarre le moniteur temps reel (capture scanner + base Firebird)
4. Ouvre Chrome/Edge en mode kiosque sur le 2eme ecran

### Demarrage automatique au boot Windows
1. `Win + R` > tapez `shell:startup` > Entree
2. Creez un raccourci vers `scripts\lancer-affichage.bat` dans ce dossier

## Configuration du double ecran

### Etendre l'affichage Windows
1. Clic droit sur le Bureau > **Parametres d'affichage**
2. Selectionnez l'ecran 2
3. Choisissez **Etendre ces affichages**
4. Notez la position de l'ecran 2

### Ajuster la position Chrome
Dans `scripts/lancer-affichage.bat`, modifiez `--window-position=1920,0` :
- Ecran 2 a droite : `--window-position=1920,0` (defaut)
- Ecran 2 a gauche : `--window-position=-1920,0`
- Remplacez `1920` par la resolution horizontale de votre ecran principal

## API REST (pour integration avancee)

Le serveur local sur le port 5555 expose une API REST :

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/status` | Etat du serveur |
| GET | `/api/transaction` | Transaction en cours |
| POST | `/api/transaction/item` | Ajouter un article |
| POST | `/api/transaction/payment` | Passer en mode paiement |
| POST | `/api/transaction/complete` | Terminer la transaction |
| POST | `/api/transaction/clear` | Vider la transaction |

Exemple - ajouter un article :
```bash
curl -X POST http://localhost:5555/api/transaction/item ^
  -H "Content-Type: application/json" ^
  -d "{\"description\": \"Baguette\", \"price\": 1.30, \"quantity\": 1}"
```

## Personnalisation

### Couleurs
```json
"colors": { "primary": "#1a237e", "accent": "#ff6f00" }
```

### Logo
Placez votre logo dans `display/` et configurez `"logo_url": "logo.png"`

### Messages promotionnels
```json
"promos": ["Offre speciale : -20% sur les fruits !"]
```

## Structure du projet

```
pc-caisse/
  config/
    config.json          # Configuration du magasin + connexion Flexo
    products.json        # Base de produits locale (codes-barres)
    transaction.json     # Etat transaction en cours (auto-genere)
  display/
    index.html           # Page d'affichage client (4 ecrans)
    style.css            # Styles
    app.js               # Logique client (polling serveur)
  scripts/
    lancer-affichage.bat # Lanceur Windows (production)
    ouvrir-demo.bat      # Lanceur mode demo
    flexo_monitor.py     # Moniteur temps reel (scanner + Firebird)
    explorer_base.py     # Outil pour explorer la base Flexo 6
  server/
    server.py            # Serveur HTTP local + API REST
```

## Depannage

| Probleme | Solution |
|----------|----------|
| "Python n'est pas reconnu" | Reinstallez Python en cochant "Add to PATH" |
| L'ecran s'ouvre sur le mauvais moniteur | Ajustez `--window-position` dans le .bat |
| Scanner non detecte | Verifiez que `pynput` est installe (`pip install pynput`) |
| Pas de connexion Firebird | Verifiez `flexo_db_path` dans config.json, lancez `explorer_base.py` |
| Page blanche | Verifiez le serveur: http://localhost:5555/api/status |
| Articles sans prix | Completez `config/products.json` avec vos produits |
