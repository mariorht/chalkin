/* utils.js - Funciones de utilidad compartidas */

const Utils = {
    /**
     * Formatea una fecha como badge relativo (Hoy, Ayer, Hace X días, etc.)
     */
    formatDateBadge(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        
        // Comparar solo las fechas (sin hora)
        const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
        const todayOnly = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const diffDays = Math.round((todayOnly - dateOnly) / 86400000);

        if (diffDays === 0) return 'Hoy';
        if (diffDays === 1) return 'Ayer';
        if (diffDays < 7) return `Hace ${diffDays} días`;
        
        return date.toLocaleDateString('es-ES', { 
            day: 'numeric', 
            month: 'short',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    },

    /**
     * Extrae día y mes de una fecha para mostrar en el icono
     */
    formatDateIcon(dateStr) {
        const date = new Date(dateStr);
        return {
            day: date.getDate(),
            month: date.toLocaleDateString('es', { month: 'short' })
        };
    },

    /**
     * Obtiene mes y año de una fecha (para agrupación)
     */
    getMonthYear(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('es', { month: 'long', year: 'numeric' });
    },

    /**
     * Calcula la duración entre dos fechas
     */
    formatDuration(startedAt, endedAt) {
        if (!endedAt) return null;
        const start = new Date(startedAt);
        const end = new Date(endedAt);
        const diffMs = end - start;
        const hours = Math.floor(diffMs / 3600000);
        const mins = Math.floor((diffMs % 3600000) / 60000);
        
        if (hours > 0) {
            return `${hours}h ${mins}min`;
        }
        return `${mins} min`;
    },

    /**
     * Genera headers para peticiones autenticadas
     */
    getHeaders(token) {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }
};

// Exportar para uso global
window.Utils = Utils;
