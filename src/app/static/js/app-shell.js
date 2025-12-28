/* =============================================
   App Shell - JavaScript compartido para Chalkin
   Maneja autenticación, navegación y funcionalidades comunes
   ============================================= */

const AppShell = {
    API_URL: '/api',
    
    // Estado del usuario
    user: null,
    token: null,
    
    // Inicializar el app shell
    init: function(options = {}) {
        this.token = localStorage.getItem('token');
        this.loadUser();
        
        // Verificar autenticación si es requerido
        if (options.requireAuth !== false && !this.token) {
            window.location.href = '/login';
            return false;
        }
        
        // Renderizar el shell
        this.renderHeader();
        this.renderBottomNav(options.activePage || '');
        
        // Cargar notificaciones de amigos
        if (this.token) {
            this.loadFriendRequestsCount();
            // TODO: Push notifications desactivadas temporalmente (requiere HTTPS)
            // this.setupPush();
        }
        
        // Añadir clase al body
        document.body.classList.add('has-app-shell');
        
        return true;
    },

    // Registrar service worker y suscribir push
    setupPush: async function() {
        // DESACTIVADO TEMPORALMENTE - Descomentar cuando se quiera usar
        return;
        /*
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
        if (Notification.permission === 'denied') return;
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            await navigator.serviceWorker.ready;

            // Obtener public key
            const keyRes = await fetch(`${this.API_URL}/notifications/public-key`);
            if (!keyRes.ok) return;
            const { public_key } = await keyRes.json();
            if (!public_key) return;

            // Revisar suscripción existente
            let subscription = await registration.pushManager.getSubscription();
            if (!subscription) {
                subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: this.urlBase64ToUint8Array(public_key)
                });
            }

            // Enviar suscripción al backend
            const payload = {
                endpoint: subscription.endpoint,
                p256dh: this.arrayBufferToBase64(subscription.getKey('p256dh')),
                auth: this.arrayBufferToBase64(subscription.getKey('auth'))
            };

            await fetch(`${this.API_URL}/notifications/subscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify(payload)
            });
        } catch (e) {
            console.warn('Push setup failed', e);
        }
        */
    },

    urlBase64ToUint8Array: function(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    },

    arrayBufferToBase64: function(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    },
    
    // Cargar datos del usuario desde localStorage
    loadUser: function() {
        try {
            const userStr = localStorage.getItem('user');
            if (userStr && userStr !== 'undefined') {
                this.user = JSON.parse(userStr);
            }
        } catch (e) {
            console.error('Error parsing user:', e);
            this.user = {};
        }
    },
    
    // Obtener inicial del usuario
    getUserInitial: function() {
        if (this.user && this.user.username) {
            return this.user.username.charAt(0).toUpperCase();
        }
        return '?';
    },
    
    // Obtener foto de perfil
    getProfilePicture: function() {
        return (this.user && this.user.profile_picture) || null;
    },
    
    // Obtener nombre de usuario
    getUsername: function() {
        return (this.user && this.user.username) || 'Usuario';
    },
    
    // Renderizar el header
    renderHeader: function() {
        const existingHeader = document.querySelector('.app-header');
        if (existingHeader) {
            existingHeader.remove();
        }
        
        const header = document.createElement('header');
        header.className = 'app-header';
        
        const profilePic = this.getProfilePicture();
        const avatarContent = profilePic 
            ? `<img src="${profilePic}" alt="Perfil">` 
            : this.getUserInitial();
        
        header.innerHTML = `
            <a href="/dashboard" class="logo">
                <span class="logo-icon"><img src="/static/icons/logoChalkin_v2_48.png" alt="Chalkin"></span>
                <span>Chalkin</span>
            </a>
            <div class="user-section">
                <span class="user-name">${this.getUsername()}</span>
                <a href="/profile" class="user-avatar" title="${this.getUsername()}">${avatarContent}</a>
                <button class="btn-logout" onclick="AppShell.logout()">Salir</button>
            </div>
        `;
        
        document.body.insertBefore(header, document.body.firstChild);
    },
    
    // Renderizar la navegación inferior
    renderBottomNav: function(activePage) {
        const existingNav = document.querySelector('.bottom-nav');
        if (existingNav) {
            existingNav.remove();
        }
        
        const nav = document.createElement('nav');
        nav.className = 'bottom-nav';
        nav.id = 'bottomNav';
        
        const navItems = [
            { id: 'dashboard', href: '/dashboard', icon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>', label: 'Inicio' },
            { id: 'profile', href: `/users?id=${this.user?.id || ''}`, icon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>', label: 'Yo' },
            { id: 'feed', href: '/feed', icon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V8l-5-5zM7 7h5v2H7V7zm10 10H7v-2h10v2zm0-4H7v-2h10v2z"/></svg>', label: 'Feed' },
            { id: 'stats', href: '/stats', icon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/></svg>', label: 'Stats' },
            { id: 'gyms', href: '/gyms', icon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z"/></svg>', label: 'Gyms' }
        ];
        
        nav.innerHTML = navItems.map(item => `
            <a href="${item.href}" class="${activePage === item.id ? 'active' : ''}" data-nav="${item.id}">
                <span class="nav-icon">${item.icon}</span>
                ${item.hasBadge ? '<span class="nav-badge" id="friendsBadge" style="display: none;">0</span>' : ''}
            </a>
        `).join('');
        
        document.body.appendChild(nav);
    },
    
    // Cargar contador de solicitudes de amistad
    loadFriendRequestsCount: async function() {
        try {
            const response = await this.fetchWithAuth(`${this.API_URL}/social/friends/requests`);
            if (!response || !response.ok) return;
            
            const requests = await response.json();
            const badge = document.getElementById('friendsBadge');
            
            if (badge && requests.length > 0) {
                badge.textContent = requests.length > 9 ? '9+' : requests.length;
                badge.style.display = 'flex';
            }
        } catch (error) {
            console.error('Error loading friend requests count:', error);
        }
    },
    
    // Actualizar badge de amigos
    updateFriendsBadge: function(count) {
        const badge = document.getElementById('friendsBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 9 ? '9+' : count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    },
    
    // Fetch con autenticación
    fetchWithAuth: async function(url, options = {}) {
        const headers = {
            ...options.headers,
            'Authorization': `Bearer ${this.token}`
        };
        
        const response = await fetch(url, { ...options, headers });
        
        if (response.status === 401) {
            this.logout();
            return null;
        }
        
        return response;
    },
    
    // Cerrar sesión
    logout: function() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    },
    
    // Establecer página activa
    setActivePage: function(pageId) {
        const navLinks = document.querySelectorAll('.bottom-nav a');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.dataset.nav === pageId) {
                link.classList.add('active');
            }
        });
    }
};

// Exponer globalmente
window.AppShell = AppShell;
