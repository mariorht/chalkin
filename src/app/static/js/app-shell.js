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
        }
        
        // Añadir clase al body
        document.body.classList.add('has-app-shell');
        
        return true;
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
                <span class="logo-icon">🧗</span>
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
            { id: 'dashboard', href: '/dashboard', icon: '🏠', label: 'Inicio' },
            { id: 'sessions', href: '/sessions', icon: '📅', label: 'Sesiones' },
            { id: 'feed', href: '/feed', icon: '📰', label: 'Feed' },
            { id: 'stats', href: '/stats', icon: '📊', label: 'Stats' },
            { id: 'gyms', href: '/gyms', icon: '🏢', label: 'Gyms' }
        ];
        
        nav.innerHTML = navItems.map(item => `
            <a href="${item.href}" class="${activePage === item.id ? 'active' : ''}" data-nav="${item.id}">
                <span class="nav-icon">${item.icon}</span>
                <span class="nav-label">${item.label}</span>
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
