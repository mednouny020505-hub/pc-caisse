/* ============================================
   AFFICHAGE CLIENT - Application principale
   Polling du serveur local pour les données Flexo 6
   ============================================ */

(function () {
    'use strict';

    // --- Configuration ---
    const CONFIG = {
        serverUrl: 'http://localhost:5555',
        pollInterval: 500,       // ms entre chaque polling
        thankyouDuration: 5000,  // ms affichage ecran remerciement
        promoRotateInterval: 6000, // ms entre chaque promo
    };

    // --- Elements DOM ---
    const screens = {
        welcome: document.getElementById('welcome-screen'),
        transaction: document.getElementById('transaction-screen'),
        payment: document.getElementById('payment-screen'),
        thankyou: document.getElementById('thankyou-screen'),
    };

    const els = {
        storeName: document.getElementById('store-name'),
        txStoreName: document.getElementById('tx-store-name'),
        welcomeText: document.getElementById('welcome-text'),
        promoSlider: document.getElementById('promo-slider'),
        currentDate: document.getElementById('current-date'),
        currentTime: document.getElementById('current-time'),
        txDate: document.getElementById('tx-date'),
        txTime: document.getElementById('tx-time'),
        lastItemName: document.getElementById('last-item-name'),
        lastItemPrice: document.getElementById('last-item-price'),
        lastItemQty: document.getElementById('last-item-qty'),
        itemsList: document.getElementById('items-list'),
        itemsCount: document.getElementById('items-count'),
        subtotal: document.getElementById('subtotal'),
        discountRow: document.getElementById('discount-row'),
        discount: document.getElementById('discount'),
        tax: document.getElementById('tax'),
        grandTotal: document.getElementById('grand-total'),
        paymentAmount: document.getElementById('payment-amount'),
        paymentMethod: document.getElementById('payment-method'),
        paymentInfo: document.getElementById('payment-info'),
        thankyouText: document.getElementById('thankyou-text'),
    };

    // --- Etat ---
    let currentScreen = 'welcome';
    let lastItemCount = 0;
    let promoIndex = 0;
    let promoSlides = [];
    let configLoaded = false;

    // --- Utilitaires ---
    function formatPrice(amount) {
        return parseFloat(amount || 0).toFixed(2).replace('.', ',') + ' \u20ac';
    }

    function formatDate() {
        const now = new Date();
        return now.toLocaleDateString('fr-FR', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }

    function formatTime() {
        return new Date().toLocaleTimeString('fr-FR', {
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    }

    // --- Gestion des ecrans ---
    function showScreen(name) {
        if (currentScreen === name) return;
        Object.keys(screens).forEach(function (key) {
            screens[key].classList.remove('active');
        });
        // Petit delai pour la transition
        setTimeout(function () {
            screens[name].classList.add('active');
        }, 50);
        currentScreen = name;
    }

    // --- Mise a jour de l'horloge ---
    function updateClock() {
        var date = formatDate();
        var time = formatTime();
        if (els.currentDate) els.currentDate.textContent = date;
        if (els.currentTime) els.currentTime.textContent = time;
        if (els.txDate) els.txDate.textContent = date;
        if (els.txTime) els.txTime.textContent = time;
    }

    // --- Promos ---
    function setupPromos(promos) {
        if (!promos || promos.length === 0) {
            promos = ['Bienvenue dans notre magasin !'];
        }
        promoSlides = promos;
        els.promoSlider.innerHTML = '';
        promos.forEach(function (text) {
            var slide = document.createElement('div');
            slide.className = 'promo-slide';
            slide.textContent = text;
            els.promoSlider.appendChild(slide);
        });
    }

    function rotatePromo() {
        if (promoSlides.length <= 1) return;
        promoIndex = (promoIndex + 1) % promoSlides.length;
        els.promoSlider.style.transform = 'translateX(-' + (promoIndex * 100) + '%)';
    }

    // --- Rendu des articles ---
    function renderItems(items) {
        if (!items || items.length === 0) {
            els.itemsList.innerHTML = '';
            els.itemsCount.textContent = '0 article(s)';
            return;
        }

        // Mettre a jour le dernier article
        var lastItem = items[items.length - 1];
        els.lastItemName.textContent = lastItem.description || lastItem.name || '-';
        els.lastItemPrice.textContent = formatPrice(lastItem.price);
        if (lastItem.quantity && lastItem.quantity > 1) {
            els.lastItemQty.textContent = 'x' + lastItem.quantity;
        } else {
            els.lastItemQty.textContent = '';
        }

        var isNewItem = items.length > lastItemCount;
        lastItemCount = items.length;

        // Reconstruire la liste
        els.itemsList.innerHTML = '';
        items.forEach(function (item, index) {
            var row = document.createElement('div');
            row.className = 'item-row';
            if (isNewItem && index === items.length - 1) {
                row.className += ' new-item';
            }

            var total = (parseFloat(item.price) || 0) * (parseInt(item.quantity) || 1);

            row.innerHTML =
                '<span class="col-desc">' + escapeHtml(item.description || item.name || '') + '</span>' +
                '<span class="col-qty">' + (item.quantity || 1) + '</span>' +
                '<span class="col-price">' + formatPrice(item.price) + '</span>' +
                '<span class="col-total">' + formatPrice(total) + '</span>';

            els.itemsList.appendChild(row);
        });

        // Auto-scroll en bas
        els.itemsList.scrollTop = els.itemsList.scrollHeight;

        // Nombre d'articles
        var totalQty = items.reduce(function (sum, item) {
            return sum + (parseInt(item.quantity) || 1);
        }, 0);
        els.itemsCount.textContent = totalQty + ' article(s)';
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --- Rendu des totaux ---
    function renderTotals(data) {
        els.subtotal.textContent = formatPrice(data.subtotal);
        els.tax.textContent = formatPrice(data.tax);
        els.grandTotal.textContent = formatPrice(data.total);

        if (data.discount && parseFloat(data.discount) > 0) {
            els.discountRow.style.display = 'flex';
            els.discount.textContent = '-' + formatPrice(data.discount);
        } else {
            els.discountRow.style.display = 'none';
        }
    }

    // --- Chargement de la config ---
    function loadConfig() {
        fetch(CONFIG.serverUrl + '/api/config')
            .then(function (res) { return res.json(); })
            .then(function (config) {
                if (config.store_name) {
                    els.storeName.textContent = config.store_name;
                    els.txStoreName.textContent = config.store_name;
                }
                if (config.welcome_message) {
                    els.welcomeText.textContent = config.welcome_message;
                }
                if (config.thankyou_message) {
                    els.thankyouText.textContent = config.thankyou_message;
                }
                if (config.thankyou_duration) {
                    CONFIG.thankyouDuration = config.thankyou_duration;
                }
                if (config.logo_url) {
                    var logoDiv = document.getElementById('store-logo');
                    logoDiv.innerHTML = '<img src="' + config.logo_url + '" alt="Logo">';
                }
                if (config.promos) {
                    setupPromos(config.promos);
                }
                if (config.colors) {
                    var root = document.documentElement;
                    if (config.colors.primary) root.style.setProperty('--primary-color', config.colors.primary);
                    if (config.colors.accent) root.style.setProperty('--accent-color', config.colors.accent);
                }
                configLoaded = true;
            })
            .catch(function () {
                // Serveur pas encore demarre, on reessaye
                if (!configLoaded) {
                    setTimeout(loadConfig, 2000);
                }
            });
    }

    // --- Polling des donnees de transaction ---
    var thankyouTimeout = null;

    function pollTransaction() {
        fetch(CONFIG.serverUrl + '/api/transaction')
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data || !data.status) {
                    showScreen('welcome');
                    return;
                }

                switch (data.status) {
                    case 'idle':
                        lastItemCount = 0;
                        showScreen('welcome');
                        break;

                    case 'in_progress':
                        if (thankyouTimeout) {
                            clearTimeout(thankyouTimeout);
                            thankyouTimeout = null;
                        }
                        renderItems(data.items || []);
                        renderTotals(data);
                        showScreen('transaction');
                        break;

                    case 'payment':
                        els.paymentAmount.textContent = formatPrice(data.total);
                        els.paymentMethod.textContent = data.payment_method || '';
                        els.paymentInfo.textContent = data.payment_info || '';
                        showScreen('payment');
                        break;

                    case 'completed':
                        showScreen('thankyou');
                        if (!thankyouTimeout) {
                            thankyouTimeout = setTimeout(function () {
                                lastItemCount = 0;
                                thankyouTimeout = null;
                            }, CONFIG.thankyouDuration);
                        }
                        break;

                    default:
                        showScreen('welcome');
                }
            })
            .catch(function () {
                // Serveur non disponible, rester sur l'ecran d'accueil
            });
    }

    // --- Mode demo (sans serveur) ---
    function checkDemoMode() {
        var params = new URLSearchParams(window.location.search);
        if (params.get('demo') === '1') {
            runDemo();
            return true;
        }
        return false;
    }

    function runDemo() {
        setupPromos([
            'Offre speciale : -20% sur les fruits et legumes !',
            'Carte fidelite : doublez vos points ce week-end !',
            'Nouveau : livraison a domicile disponible !'
        ]);

        setTimeout(function () {
            var demoItems = [
                { description: 'Baguette tradition', price: 1.30, quantity: 2 },
                { description: 'Lait demi-ecreme 1L', price: 1.15, quantity: 1 },
                { description: 'Camembert President', price: 2.49, quantity: 1 },
                { description: 'Pommes Golden 1kg', price: 2.99, quantity: 1 },
                { description: 'Jambon blanc x6', price: 3.25, quantity: 1 },
                { description: 'Yaourt nature x12', price: 3.60, quantity: 1 },
            ];

            var items = [];
            var i = 0;

            function addNext() {
                if (i < demoItems.length) {
                    items.push(demoItems[i]);
                    i++;
                    renderItems(items.slice());
                    var subtotal = items.reduce(function (s, it) {
                        return s + (it.price * it.quantity);
                    }, 0);
                    renderTotals({
                        subtotal: subtotal,
                        tax: subtotal * 0.2,
                        total: subtotal * 1.2,
                        discount: 0
                    });
                    showScreen('transaction');
                    setTimeout(addNext, 2000);
                } else {
                    setTimeout(function () {
                        var total = items.reduce(function (s, it) {
                            return s + (it.price * it.quantity);
                        }, 0) * 1.2;
                        els.paymentAmount.textContent = formatPrice(total);
                        els.paymentMethod.textContent = 'Carte bancaire';
                        showScreen('payment');

                        setTimeout(function () {
                            showScreen('thankyou');
                            setTimeout(function () {
                                lastItemCount = 0;
                                showScreen('welcome');
                                // Relancer la demo
                                setTimeout(function () { runDemo(); }, 5000);
                            }, 5000);
                        }, 3000);
                    }, 2000);
                }
            }

            addNext();
        }, 3000);
    }

    // --- Initialisation ---
    function init() {
        updateClock();
        setInterval(updateClock, 1000);

        setupPromos([]);
        setInterval(rotatePromo, CONFIG.promoRotateInterval);

        showScreen('welcome');

        if (!checkDemoMode()) {
            loadConfig();
            setInterval(pollTransaction, CONFIG.pollInterval);
        }
    }

    // Demarrage
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
