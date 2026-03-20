# Affichage Client Double Ecran - Caisse Flexo 6

Solution d'affichage client sur le deuxieme ecran de votre caisse enregistreuse sous Flexo 6 / Windows 10.

## Fonctionnalites

- **Ecran d'accueil** : logo, nom du magasin, messages promotionnels rotatifs, horloge
- **Ecran de transaction** : articles en temps reel, dernier article scanne, totaux
- **Ecran de paiement** : montant a payer, mode de paiement
- **Ecran de remerciement** : animation de confirmation apres paiement
- **Mode demo** : test sans Flexo 6

## Pre-requis

- Windows 10
- Python 3.8+ (telecharger sur https://www.python.org/downloads/)
  - **IMPORTANT** : cocher "Add Python to PATH" lors de l'installation
- Google Chrome (recommande pour le mode kiosque plein ecran)
- Double ecran configure dans les parametres d'affichage Windows

## Installation

1. Copiez le dossier `pc-caisse` sur votre PC de caisse (ex: `C:\pc-caisse`)

2. Configurez votre magasin dans `config/config.json` :
   ```json
   {
     "store_name": "Mon Magasin",
     "welcome_message": "Bienvenue chez nous !",
     "promos": ["Promo du jour : -20% sur tout !"],
     "flexo_ticket_path": "C:\\Flexo6\\Tickets",
     "flexo_watch_enabled": true
   }
   ```

3. Configurez le chemin de vos tickets Flexo 6 dans `flexo_ticket_path`

## Utilisation

### Demarrage rapide (mode demo)
Double-cliquez sur `scripts\ouvrir-demo.bat`

### Demarrage en production
Double-cliquez sur `scripts\lancer-affichage.bat`

Ce script :
1. Demarre le serveur local (port 5555)
2. Demarre le moniteur Flexo 6
3. Ouvre Chrome en mode kiosque sur le 2eme ecran

### Demarrage automatique au boot Windows
1. Appuyez sur `Win + R`, tapez `shell:startup`, Entree
2. Creez un raccourci vers `scripts\lancer-affichage.bat` dans ce dossier

## Configuration du double ecran

### Etendre l'affichage Windows
1. Clic droit sur le Bureau > **Parametres d'affichage**
2. Selectionnez l'ecran 2
3. Choisissez **Etendre ces affichages**
4. Notez la resolution et la position (ex: 1920,0 si l'ecran 2 est a droite)

### Ajuster la position Chrome
Dans `scripts/lancer-affichage.bat`, modifiez `--window-position=1920,0` selon la position de votre 2eme ecran :
- Ecran 2 a droite : `--window-position=1920,0`
- Ecran 2 a gauche : `--window-position=-1920,0`
- Ajustez 1920 a la resolution de votre ecran principal

## Integration avec Flexo 6

Le moniteur surveille les fichiers de tickets generes par Flexo 6. Formats supportes :
- **CSV point-virgule** : `CODE;DESCRIPTION;QTE;PRIX`
- **Tabule** : `DESCRIPTION\tQTE\tPRIX`
- **Texte** : `Description  2 x 3,50  7,00`

### Chemins Flexo 6 verifies automatiquement
- `C:\Flexo6\Tickets`
- `C:\Flexo6\Data\ticket_en_cours.txt`
- `C:\Flexo6\Export`
- `C:\ProgramData\Flexo6\Tickets`

Si votre installation est ailleurs, configurez `flexo_ticket_path` dans `config/config.json`.

## API REST (pour integration avancee)

Le serveur expose une API locale sur le port 5555 :

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/status` | Etat du serveur |
| GET | `/api/transaction` | Transaction en cours |
| GET | `/api/config` | Configuration |
| POST | `/api/transaction` | Mise a jour complete |
| POST | `/api/transaction/item` | Ajouter un article |
| POST | `/api/transaction/clear` | Vider la transaction |
| POST | `/api/transaction/payment` | Mode paiement |
| POST | `/api/transaction/complete` | Terminer la transaction |

### Exemples

Ajouter un article :
```bash
curl -X POST http://localhost:5555/api/transaction/item -H "Content-Type: application/json" -d "{\"description\": \"Baguette\", \"price\": 1.30, \"quantity\": 1}"
```

Passer en mode paiement :
```bash
curl -X POST http://localhost:5555/api/transaction/payment -H "Content-Type: application/json" -d "{\"method\": \"Carte bancaire\"}"
```

Terminer la transaction :
```bash
curl -X POST http://localhost:5555/api/transaction/complete
```

## Personnalisation

### Couleurs
Modifiez `colors` dans `config/config.json` :
```json
"colors": {
  "primary": "#1a237e",
  "accent": "#ff6f00"
}
```

### Logo
Placez votre logo dans `display/` et configurez :
```json
"logo_url": "logo.png"
```

### Messages promotionnels
```json
"promos": [
  "Offre speciale : -20% sur les fruits !",
  "Carte fidelite : demandez-la en caisse !"
]
```

## Structure du projet

```
pc-caisse/
  config/
    config.json          # Configuration du magasin
    transaction.json     # Etat de la transaction (auto-genere)
  display/
    index.html           # Page d'affichage client
    style.css            # Styles
    app.js               # Logique client
  scripts/
    lancer-affichage.bat # Lanceur Windows (production)
    ouvrir-demo.bat      # Lanceur mode demo
    flexo_monitor.py     # Moniteur Flexo 6
  server/
    server.py            # Serveur HTTP local
```

## Depannage

| Probleme | Solution |
|----------|----------|
| "Python n'est pas reconnu" | Reinstallez Python en cochant "Add to PATH" |
| L'ecran s'ouvre sur le mauvais moniteur | Ajustez `--window-position` dans le .bat |
| Pas de donnees Flexo | Verifiez `flexo_ticket_path` dans config.json |
| Page blanche | Verifiez que le serveur tourne (http://localhost:5555/api/status) |
