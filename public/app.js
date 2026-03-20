// --- Données ---
let catalogue = JSON.parse(localStorage.getItem('catalogue') || '[]');
let panier = [];

// --- Éléments DOM ---
const nomProduit = document.getElementById('nom-produit');
const prixProduit = document.getElementById('prix-produit');
const btnAjouterCatalogue = document.getElementById('btn-ajouter-catalogue');
const listeProduits = document.getElementById('liste-produits');
const listePanier = document.getElementById('liste-panier');
const totalPrix = document.getElementById('total-prix');
const btnVider = document.getElementById('btn-vider');
const btnValider = document.getElementById('btn-valider');

// --- Catalogue ---
function sauvegarderCatalogue() {
  localStorage.setItem('catalogue', JSON.stringify(catalogue));
}

function afficherCatalogue() {
  listeProduits.innerHTML = '';
  catalogue.forEach((produit, index) => {
    const carte = document.createElement('div');
    carte.className = 'carte-produit';
    carte.innerHTML = `
      <div class="nom">${produit.nom}</div>
      <div class="prix">${produit.prix.toFixed(2)} €</div>
    `;
    carte.addEventListener('click', () => ajouterAuPanier(index));
    listeProduits.appendChild(carte);
  });
}

btnAjouterCatalogue.addEventListener('click', () => {
  const nom = nomProduit.value.trim();
  const prix = parseFloat(prixProduit.value);

  if (!nom || isNaN(prix) || prix < 0) return;

  catalogue.push({ nom, prix });
  sauvegarderCatalogue();
  afficherCatalogue();

  nomProduit.value = '';
  prixProduit.value = '';
  nomProduit.focus();
});

// Ajout via Enter
prixProduit.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') btnAjouterCatalogue.click();
});

// --- Panier ---
function ajouterAuPanier(indexProduit) {
  const produit = catalogue[indexProduit];
  const itemExistant = panier.find(item => item.nom === produit.nom);

  if (itemExistant) {
    itemExistant.quantite++;
  } else {
    panier.push({ nom: produit.nom, prix: produit.prix, quantite: 1 });
  }

  afficherPanier();
}

function afficherPanier() {
  if (panier.length === 0) {
    listePanier.innerHTML = '<div class="panier-vide">Le panier est vide</div>';
    totalPrix.textContent = '0.00 €';
    return;
  }

  listePanier.innerHTML = '';
  let total = 0;

  panier.forEach((item, index) => {
    const sousTotal = item.prix * item.quantite;
    total += sousTotal;

    const div = document.createElement('div');
    div.className = 'item-panier';
    div.innerHTML = `
      <div class="info">
        <div class="nom-item">${item.nom}</div>
        <div class="prix-item">${item.prix.toFixed(2)} € / unité</div>
      </div>
      <div class="quantite">
        <button class="btn-suppr" data-index="${index}" data-action="moins">-</button>
        <span>${item.quantite}</span>
        <button data-index="${index}" data-action="plus">+</button>
      </div>
      <div class="sous-total">${sousTotal.toFixed(2)} €</div>
    `;
    listePanier.appendChild(div);
  });

  totalPrix.textContent = total.toFixed(2) + ' €';

  // Événements boutons quantité
  listePanier.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      const index = parseInt(btn.dataset.index);
      if (btn.dataset.action === 'plus') {
        panier[index].quantite++;
      } else {
        panier[index].quantite--;
        if (panier[index].quantite <= 0) {
          panier.splice(index, 1);
        }
      }
      afficherPanier();
    });
  });
}

// Vider le panier
btnVider.addEventListener('click', () => {
  panier = [];
  afficherPanier();
});

// Valider (affiche un résumé)
btnValider.addEventListener('click', () => {
  if (panier.length === 0) return;

  const total = panier.reduce((sum, item) => sum + item.prix * item.quantite, 0);
  alert(`Achat validé !\nTotal : ${total.toFixed(2)} €\nMerci !`);
  panier = [];
  afficherPanier();
});

// --- Init ---
afficherCatalogue();
afficherPanier();
